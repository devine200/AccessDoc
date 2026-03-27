import re

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from accessdoc.views import serve_publish_build


def _doc_mount_regex() -> str:
    """
    Path segment(s) under which each static build is served, derived from
    ``DOCUSAURUS_BASE_URL`` (e.g. ``/viewer/`` → ``viewer``, ``/docs/`` → ``docs``).
    Must stay in sync with ``viewer_item_docs_url`` and the pipeline build env.
    """
    raw = (settings.DOCUSAURUS_BASE_URL or "").strip("/")
    if not raw:
        return "viewer"
    return "/".join(re.escape(p) for p in raw.split("/") if p)


# PublishedItem primary key (UUID)
_VIEWER_ID = (
    r"(?P<publish_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)

_MOUNT = _doc_mount_regex()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("items.urls")),
    re_path(
        rf"^{_MOUNT}/{_VIEWER_ID}/$",
        serve_publish_build,
        kwargs={"path": ""},
        name="viewer_item",
    ),
    re_path(
        rf"^{_MOUNT}/{_VIEWER_ID}/(?P<path>.+)$",
        serve_publish_build,
        name="viewer_item_path",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
