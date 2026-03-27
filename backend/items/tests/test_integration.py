from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client, TestCase, RequestFactory, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accessdoc.views import serve_publish_build
from items.models import PublishedItem
from items.tasks import process_published_item
from items.utils import slugify_label, unique_slug, viewer_item_docs_url
from utils.main import (
    RESERVED_DOC_IDS,
    _allocate_doc_id,
    _stem_matching_docusaurus_default_id,
)


def _input_pdf_path(filename: str) -> Path:
    path = Path(settings.UTILS_DIR).resolve() / "input_files" / filename
    if not path.is_file():
        raise unittest.SkipTest(f"Fixture PDF not found: {path}")
    return path


def _content_file_from_input_files(filename: str) -> ContentFile:
    p = _input_pdf_path(filename)
    return ContentFile(p.read_bytes(), name=p.name)


def _simple_uploaded_file_from_input_files(filename: str) -> SimpleUploadedFile:
    p = _input_pdf_path(filename)
    return SimpleUploadedFile(
        p.name,
        p.read_bytes(),
        content_type="application/pdf",
    )


def _doc_mount_segment() -> str:
    """Match ``accessdoc.urls`` mount derived from ``DOCUSAURUS_BASE_URL`` (no overrides)."""
    raw = (settings.DOCUSAURUS_BASE_URL or "").strip("/")
    return raw or "viewer"


class PublishedItemAPITests(TestCase):
    """Read-only API lists and retrieves only READY items."""

    def setUp(self):
        self.api = APIClient()
        self.ready = PublishedItem.objects.create(
            slug="ready-doc",
            title="Ready",
            description="d",
            status=PublishedItem.Status.READY,
            page_count=2,
            source_file=_content_file_from_input_files("text.pdf"),
        )
        self.pending = PublishedItem.objects.create(
            slug="pending-doc",
            title="Pending",
            description="d",
            status=PublishedItem.Status.PENDING,
            source_file=_content_file_from_input_files("scanned.pdf"),
        )

    def test_list_only_ready(self):
        r = self.api.get("/api/items/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in r.json()}
        self.assertIn(str(self.ready.pk), ids)
        self.assertNotIn(str(self.pending.pk), ids)

    def test_retrieve_ready(self):
        r = self.api.get(f"/api/items/{self.ready.pk}/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        body = r.json()
        self.assertEqual(body["slug"], "ready-doc")
        self.assertEqual(body["status"], PublishedItem.Status.READY)
        self.assertEqual(body["page_count"], 2)

    def test_retrieve_pending_returns_404(self):
        r = self.api.get(f"/api/items/{self.pending.pk}/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)


class UploadFlowTests(TestCase):
    """Staff upload creates a pending item and schedules processing."""

    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staffer",
            email="s@example.com",
            password="secret123",
            is_staff=True,
        )

    def test_anonymous_redirected_from_upload(self):
        r = self.client.get(reverse("upload"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    def test_anonymous_dashboard_json_forbidden(self):
        r = self.client.get(reverse("dashboard_items_json"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])

    @patch("items.views.schedule_process_published_item")
    def test_staff_upload_success(self, mock_schedule: MagicMock):
        self.client.login(username="staffer", password="secret123")
        pdf = _simple_uploaded_file_from_input_files("text.pdf")
        r = self.client.post(
            reverse("upload"),
            {
                "title": "Annual Report",
                "description": "Public copy",
                "source_file": pdf,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("dashboard"))
        item = PublishedItem.objects.get(title="Annual Report")
        self.assertEqual(item.status, PublishedItem.Status.PENDING)
        self.assertTrue(item.slug.startswith("annual-report"))
        self.assertTrue(
            str(item.source_file.name).lower().endswith(".pdf"),
            "Stored upload should remain a PDF file.",
        )
        mock_schedule.assert_called_once_with(str(item.pk))

    def test_staff_upload_rejects_non_pdf(self):
        self.client.login(username="staffer", password="secret123")
        bad = SimpleUploadedFile(
            "x.txt",
            b"not a pdf",
            content_type="text/plain",
        )
        r = self.client.post(
            reverse("upload"),
            {"title": "T", "description": "", "source_file": bad},
        )
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "Only PDF", status_code=400, html=False)

    def test_staff_upload_rejects_pdf_extension_without_pdf_header(self):
        self.client.login(username="staffer", password="secret123")
        disguised = SimpleUploadedFile(
            "disguised.pdf",
            b"<!DOCTYPE html><html></html>",
            content_type="application/pdf",
        )
        r = self.client.post(
            reverse("upload"),
            {"title": "Bad", "description": "", "source_file": disguised},
        )
        self.assertEqual(r.status_code, 400)
        self.assertContains(
            r,
            "valid PDF",
            status_code=400,
            html=False,
        )


class ProcessItemTaskIntegrationTests(TestCase):
    """Task updates model state; ``items.tasks.run_pdf_pipeline`` is mocked (avoids real ``npm run build``)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="p", is_staff=True
        )
        pdf = _simple_uploaded_file_from_input_files("text.pdf")
        self.item = PublishedItem.objects.create(
            slug="task-doc",
            title="Task doc",
            description="",
            source_file=pdf,
            status=PublishedItem.Status.PENDING,
            created_by=self.user,
        )

    @patch("items.tasks.run_pdf_pipeline")
    def test_task_marks_ready_on_success(self, mock_run: MagicMock):
        mock_run.return_value = {"page_count": 5}
        process_published_item.run(str(self.item.pk))
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, PublishedItem.Status.READY)
        self.assertEqual(self.item.page_count, 5)
        self.assertIsNotNone(self.item.processed_at)
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["publish_id"], str(self.item.pk))
        self.assertIn("DOCUSAURUS_BASE_URL", kwargs["build_env"])
        self.assertIn(
            f"/{self.item.pk}/",
            kwargs["build_env"]["DOCUSAURUS_BASE_URL"],
        )
        self.assertIn("DOCUSAURUS_SITE_TITLE", kwargs["build_env"])
        self.assertEqual(
            kwargs["docusaurus_root"],
            str(settings.DOCUSAURUS_ROOT),
        )
        self.assertEqual(
            kwargs["builds_root"],
            str(settings.DOCUSAURUS_BUILDS_ROOT),
        )

    @patch("items.tasks.run_pdf_pipeline", side_effect=RuntimeError("npm failed"))
    def test_task_marks_failed_on_pipeline_error(self, _mock_run: MagicMock):
        with self.assertRaises(RuntimeError):
            process_published_item.run(str(self.item.pk))
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, PublishedItem.Status.FAILED)
        self.assertIn("npm failed", self.item.error_message)


class ViewerHttpIntegrationTests(TestCase):
    """Full HTTP flow to ``serve_publish_build`` via URLconf (mount from settings)."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.build_root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)
        self.client = Client()
        self.pub_id = "b2c3d4e5-f6a7-4890-b123-456789abcdef"
        self.item_root = self.build_root / self.pub_id
        self.item_root.mkdir(parents=True)
        intro_dir = self.item_root / "docs" / "intro"
        intro_dir.mkdir(parents=True)
        (intro_dir / "index.html").write_text(
            "<!doctype html><html><title>Intro page</title></html>",
            encoding="utf-8",
        )

    def test_get_docs_intro_returns_200(self):
        mount = _doc_mount_segment()
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            r = self.client.get(f"/{mount}/{self.pub_id}/docs/intro/")
        self.assertEqual(r.status_code, 200)
        body = b"".join(r.streaming_content)
        self.assertIn(b"Intro page", body)

    def test_get_build_root_redirects_to_intro_without_site_index(self):
        mount = _doc_mount_segment()
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            r = self.client.get(f"/{mount}/{self.pub_id}/")
        self.assertEqual(r.status_code, 302)
        loc = r["Location"]
        self.assertIn("docs/intro", loc)

    def test_get_unknown_publish_id_returns_404(self):
        mount = _doc_mount_segment()
        ghost = "deadbeef-dead-4ead-beef-deadbeefdead"
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            r = self.client.get(f"/{mount}/{ghost}/docs/intro/")
        self.assertEqual(r.status_code, 404)

    def test_get_asset_under_build(self):
        img_dir = self.item_root / "img"
        img_dir.mkdir()
        (img_dir / "badge.png").write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        )
        mount = _doc_mount_segment()
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            r = self.client.get(f"/{mount}/{self.pub_id}/img/badge.png")
        self.assertEqual(r.status_code, 200)


class DashboardViewerUrlIntegrationTests(TestCase):
    """Dashboard JSON exposes viewer links keyed by publish id (UUID)."""

    def setUp(self):
        self.client = Client()
        User.objects.create_user(
            username="dashstaff",
            email="d@example.com",
            password="secret123",
            is_staff=True,
        )
        self.client.login(username="dashstaff", password="secret123")
        self.item = PublishedItem.objects.create(
            slug="viewer-ready",
            title="Has viewer",
            description="",
            status=PublishedItem.Status.READY,
            page_count=3,
            source_file=_content_file_from_input_files("text.pdf"),
        )

    def test_dashboard_items_json_viewer_url_uses_item_pk_and_intro_path(self):
        r = self.client.get(reverse("dashboard_items_json"))
        self.assertEqual(r.status_code, 200)
        rows = r.json()["items"]
        row = next(x for x in rows if x["id"] == str(self.item.pk))
        self.assertEqual(row["viewer_docs_url"], viewer_item_docs_url(str(self.item.pk)))
        self.assertIn(str(self.item.pk), row["viewer_docs_url"])
        self.assertTrue(row["viewer_docs_url"].rstrip("/").endswith("/docs/intro"))

    def test_pending_item_has_empty_viewer_url(self):
        PublishedItem.objects.create(
            slug="not-ready",
            title="Waiting",
            description="",
            status=PublishedItem.Status.PENDING,
            source_file=_content_file_from_input_files("scanned.pdf"),
        )
        r = self.client.get(reverse("dashboard_items_json"))
        self.assertEqual(r.status_code, 200)
        pending_rows = [
            x for x in r.json()["items"] if x["status"] == PublishedItem.Status.PENDING
        ]
        self.assertTrue(any(x["viewer_docs_url"] == "" for x in pending_rows))


class ViewerServeTests(TestCase):
    """Django serves each item's Docusaurus build under /viewer/<uuid>/."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.build_root = Path(self._td.name)
        self.addCleanup(self._td.cleanup)
        self.client = Client()
        self.pub_id = "a1b2c3d4-e5f6-4789-a012-3456789abcde"
        self.item_root = self.build_root / self.pub_id
        self.item_root.mkdir(parents=True, exist_ok=True)

    def test_serves_index_at_root(self):
        (self.item_root / "index.html").write_text("<html>ok</html>", encoding="utf-8")
        factory = RequestFactory()
        request = factory.get(f"/viewer/{self.pub_id}/")
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            response = serve_publish_build(request, publish_id=self.pub_id, path="")
        self.assertEqual(response.status_code, 200)
        body = b"".join(response.streaming_content)
        self.assertIn(b"ok", body)

    def test_path_escape_returns_404(self):
        (self.item_root / "index.html").write_text("<html>x</html>", encoding="utf-8")
        factory = RequestFactory()
        request = factory.get(f"/viewer/{self.pub_id}/")
        with override_settings(DOCUSAURUS_BUILDS_ROOT=self.build_root):
            with self.assertRaises(Http404):
                serve_publish_build(
                    request, publish_id=self.pub_id, path="../../../invalid"
                )


class DeletePublishedItemArtifactsTests(TestCase):
    """Deleting an item removes its viewer build tree and stored PDF (``pre_delete``)."""

    def test_pre_delete_removes_doc_build_and_source_file(self):
        media = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(media, ignore_errors=True))
        pdf = _content_file_from_input_files("text.pdf")
        with override_settings(MEDIA_ROOT=media, DOCUSAURUS_BUILDS_ROOT=media / "doc_builds"):
            item = PublishedItem.objects.create(
                slug="artifact-clean",
                title="Artifact clean",
                description="",
                status=PublishedItem.Status.READY,
                source_file=pdf,
            )
            build_dir = media / "doc_builds" / str(item.pk)
            build_dir.mkdir(parents=True)
            (build_dir / "index.html").write_text("<html>x</html>", encoding="utf-8")
            source_path = Path(item.source_file.path)
            self.assertTrue(source_path.is_file())
            self.assertTrue(build_dir.is_dir())
            item.delete()
            self.assertFalse(build_dir.exists())
            self.assertFalse(source_path.exists())


class DocusaurusDocIdIntegrationTests(TestCase):
    """Slugs align with Docusaurus default doc ids (numeric ``NN-`` filename prefixes)."""

    def test_stem_strips_ordering_prefix_like_docusaurus(self):
        self.assertEqual(
            _stem_matching_docusaurus_default_id("2 Background", 1),
            "background",
        )
        self.assertEqual(
            _stem_matching_docusaurus_default_id("3 Methodology", 2),
            "methodology",
        )

    def test_stem_collision_after_strip_gets_suffix_via_allocate(self):
        used = set(RESERVED_DOC_IDS)
        a = _allocate_doc_id("2 Foo", 1, used)
        used.add(a)
        b = _allocate_doc_id("3 Foo", 2, used)
        self.assertEqual(a, "foo")
        self.assertEqual(b, "foo-2")


class ViewerItemDocsUrlTests(TestCase):
    def test_viewer_item_docs_url_normalizes_prefix(self):
        with override_settings(DOCUSAURUS_BASE_URL="/docs/"):
            u = viewer_item_docs_url("11111111-2222-4333-8444-555555555555")
            self.assertEqual(
                u,
                "/docs/11111111-2222-4333-8444-555555555555/docs/intro/",
            )
        with override_settings(DOCUSAURUS_BASE_URL="viewer"):
            u = viewer_item_docs_url("aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee")
            self.assertEqual(
                u,
                "/viewer/aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee/docs/intro/",
            )


class SlugUtilTests(TestCase):
    def test_slugify_label(self):
        self.assertEqual(slugify_label("Hello World!"), "hello-world")

    def test_unique_slug_appends_when_taken(self):
        PublishedItem.objects.create(
            slug="foo",
            title="Foo",
            status=PublishedItem.Status.PENDING,
            source_file=_content_file_from_input_files("text.pdf"),
        )

        def taken(s: str) -> bool:
            return PublishedItem.objects.filter(slug=s).exists()

        u = unique_slug("foo", taken)
        self.assertTrue(u.startswith("foo-"))
        self.assertNotEqual(u, "foo")
