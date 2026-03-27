import logging
import shutil
import tempfile
import threading
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from items.models import PublishedItem
from utils.pipeline import run_pdf_pipeline

logger = logging.getLogger(__name__)


def _run_process_after_commit(item_id: str) -> None:
    """DB connections safe for use from a Celery worker or a short-lived thread."""
    close_old_connections()
    try:
        process_published_item.run(item_id)
    finally:
        close_old_connections()


def schedule_process_published_item(item_pk: str) -> None:
    """
    Queue PDF processing after the current request's transaction commits so the
    row and uploaded file exist before the task runs.

    Uses Celery when ``ACCESSDOC_USE_CELERY`` is True; otherwise a daemon thread
    (typical local dev without a worker).
    """

    def _enqueue() -> None:
        if settings.ACCESSDOC_USE_CELERY:
            process_published_item.delay(item_pk)
            logger.info("Queued process_published_item via Celery for %s", item_pk)
        else:
            t = threading.Thread(
                target=_run_process_after_commit,
                args=(item_pk,),
                daemon=True,
                name=f"accessdoc-pdf-{item_pk[:8]}",
            )
            t.start()
            logger.info("Started background thread for process_published_item %s", item_pk)

    transaction.on_commit(_enqueue)


@shared_task
def process_published_item(item_id: str):
    """Run PDF extraction, sync into Docusaurus, run static build."""
    item = PublishedItem.objects.get(pk=item_id)
    item.status = PublishedItem.Status.PROCESSING
    item.error_message = ""
    item.save(update_fields=["status", "error_message"])

    workdir = Path(tempfile.mkdtemp(prefix=f"accessdoc-{item.pk}-"))
    try:
        pdf_path = item.source_file.path
        publish_id = str(item.pk)
        viewer_prefix = settings.DOCUSAURUS_BASE_URL.rstrip("/")
        build_env = {
            "DOCUSAURUS_BASE_URL": f"{viewer_prefix}/{publish_id}/",
            "DOCUSAURUS_SITE_TITLE": item.title,
        }

        result = run_pdf_pipeline(
            pdf_path,
            work_dir=str(workdir),
            publish_id=publish_id,
            title=item.title,
            description=item.description,
            docusaurus_root=str(settings.DOCUSAURUS_ROOT),
            builds_root=str(settings.DOCUSAURUS_BUILDS_ROOT),
            build_env=build_env,
            run_build=True,
        )
        item.status = PublishedItem.Status.READY
        item.page_count = result.get("page_count")
        item.processed_at = timezone.now()
        item.save(
            update_fields=["status", "page_count", "processed_at", "error_message"]
        )
    except Exception as exc:
        item.status = PublishedItem.Status.FAILED
        item.error_message = str(exc)[:2000]
        item.processed_at = timezone.now()
        item.save(update_fields=["status", "error_message", "processed_at"])
        raise
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
