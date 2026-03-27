import re
import uuid


def viewer_item_docs_url(item_id: str, *, base_url: str | None = None) -> str:
    """
    Public URL for a ready item's viewer (intro doc).

    ``item_id`` is ``str(PublishedItem.pk)`` (UUID). ``base_url`` should match
    ``settings.DOCUSAURUS_BASE_URL`` (e.g. ``/viewer/``).
    """
    from django.conf import settings

    raw = base_url if base_url is not None else settings.DOCUSAURUS_BASE_URL
    prefix = (raw or "").rstrip("/")
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return f"{prefix}/{item_id}/docs/intro/"


def slugify_label(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", label.strip()).strip("-").lower()
    return s or "document"


def unique_slug(base: str, exists) -> str:
    candidate = base[:200]
    if not exists(candidate):
        return candidate
    suffix = uuid.uuid4().hex[:8]
    trimmed = base[: (200 - len(suffix) - 1)]
    return f"{trimmed}-{suffix}"
