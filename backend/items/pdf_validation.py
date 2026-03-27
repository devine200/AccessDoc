"""Server-side checks that an uploaded file is a PDF."""

from __future__ import annotations

# PDF headers appear within the first 1024 bytes in normal (and linearized) files.
_PDF_HEADER_WINDOW = 1024
_PDF_MARKER = b"%PDF-"


def pdf_upload_rejection_reason(upload) -> str | None:
    """
    Return a user-facing error message if ``upload`` must be rejected, else ``None``.

    Requires ``.pdf`` extension (case-insensitive) and a ``%PDF-`` header in the
    first 1KiB so Content-Type / filename cannot bypass checks alone.
    """
    name = (upload.name or "").lower()
    if not name.endswith(".pdf"):
        return "Only PDF uploads are accepted. Use a file with a .pdf extension."

    chunk = upload.read(_PDF_HEADER_WINDOW)
    if hasattr(upload, "seek"):
        upload.seek(0)

    if _PDF_MARKER not in chunk:
        return "Only valid PDF files are accepted (file does not contain a PDF header)."

    return None
