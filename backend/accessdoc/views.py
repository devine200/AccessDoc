import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect


def serve_publish_build(request, publish_id, path=""):
    """
    Serve one Docusaurus production build from ``DOCUSAURUS_BUILDS_ROOT/<PublishedItem.pk>``.

    Resolves deep links and ``index.html`` inside route segments the same way as a static host.
    """
    builds_root = Path(settings.DOCUSAURUS_BUILDS_ROOT).resolve()
    root = (builds_root / publish_id).resolve()
    if not str(root).startswith(str(builds_root)) or root == builds_root:
        raise Http404("Invalid path")
    if not root.is_dir():
        raise Http404("Not found")

    rel = (path or "").strip("/")

    if rel and ".." in Path(rel).parts:
        raise Http404("Invalid path")

    if not rel:
        index = root / "index.html"
        if index.is_file():
            return _file_response(index, status=200)
        intro_index = root / "docs" / "intro" / "index.html"
        if intro_index.is_file():
            prefix = request.path if request.path.endswith("/") else f"{request.path}/"
            return HttpResponseRedirect(f"{prefix}docs/intro/")
        raise Http404("Not found")

    candidates: list[Path] = []
    direct = (root / rel).resolve()
    if not str(direct).startswith(str(root)):
        raise Http404("Invalid path")
    candidates.append(direct)
    if direct.is_dir() or not direct.is_file():
        candidates.append((root / rel / "index.html").resolve())
    if not direct.suffix and not direct.is_dir():
        candidates.append((root / (rel + ".html")).resolve())

    seen: set[Path] = set()
    ordered: list[Path] = []
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        ordered.append(c)

    for candidate in ordered:
        if candidate.is_file() and str(candidate.resolve()).startswith(str(root)):
            return _file_response(candidate, status=200)

    not_found = root / "404.html"
    if not_found.is_file():
        return _file_response(not_found, status=404)

    raise Http404("Not found")


def _file_response(path: Path, *, status: int) -> FileResponse:
    content_type, _ = mimetypes.guess_type(str(path))
    resp = FileResponse(path.open("rb"), content_type=content_type or "text/html")
    resp.status_code = status
    return resp
