import hashlib
import os
import re
from dataclasses import dataclass

import fitz  # PyMuPDF
import pytesseract
from PIL import Image


@dataclass
class OutputLayout:
    """Resolved paths for PDF extraction output."""

    root: str

    @property
    def images(self) -> str:
        return os.path.join(self.root, "images")

    @property
    def pages(self) -> str:
        return os.path.join(self.root, "pages")


def ensure_layout_dirs(layout: OutputLayout) -> None:
    os.makedirs(layout.images, exist_ok=True)
    os.makedirs(layout.pages, exist_ok=True)


def save_image(image_bytes: bytes, layout: OutputLayout) -> str:
    hash_name = hashlib.md5(image_bytes, usedforsecurity=False).hexdigest()
    path = os.path.join(layout.images, f"{hash_name}.png")

    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(image_bytes)

    return f"images/{hash_name}.png"


def should_use_ocr(text: str) -> bool:
    text = text.strip()

    if len(text) < 50:
        return True

    words = text.split()
    if len(words) < 10:
        return True

    return False


def ocr_page(page, page_index: int) -> str:
    pix = page.get_pixmap()
    img_path = f"temp_page_{page_index}.png"
    pix.save(img_path)

    img = Image.open(img_path)
    text = pytesseract.image_to_string(img)

    os.remove(img_path)
    return text


def is_same_line(b1, b2, threshold=5):
    return abs(b1["bbox"][1] - b2["bbox"][1]) < threshold


def group_lines(blocks):
    lines = []
    current_line = []

    for block in blocks:
        if not current_line:
            current_line.append(block)
            continue

        if is_same_line(current_line[-1], block):
            current_line.append(block)
        else:
            lines.append(current_line)
            current_line = [block]

    if current_line:
        lines.append(current_line)

    return lines


def merge_line(line):
    line = sorted(line, key=lambda b: b["bbox"][0])

    text_parts = [b["text"] for b in line if b["type"] == "text"]

    return " ".join(text_parts).strip()


def process_page(doc, page, page_index: int, layout: OutputLayout):
    raw_blocks = page.get_text("dict")["blocks"]

    page_data = {
        "id": f"page-{page_index+1}",
        "page_number": page_index + 1,
        "width": page.rect.width,
        "height": page.rect.height,
        "blocks": [],
    }

    extracted_text = page.get_text()

    if should_use_ocr(extracted_text):
        print(f"⚠️ OCR triggered on page {page_index+1}")

        ocr_text = ocr_page(page, page_index)

        y_cursor = 0

        for line in ocr_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            page_data["blocks"].append(
                {
                    "type": "text",
                    "text": line,
                    "bbox": [0, y_cursor, 500, y_cursor + 10],
                    "font_size": None,
                }
            )

            y_cursor += 15

        return page_data

    for block in raw_blocks:
        if block["type"] == 0:
            text = ""
            font_size = None

            for line in block["lines"]:
                for span in line["spans"]:
                    text += span["text"]
                    if font_size is None:
                        font_size = span["size"]

            text = text.strip()

            if not text:
                continue

            page_data["blocks"].append(
                {
                    "type": "text",
                    "text": text,
                    "bbox": block["bbox"],
                    "font_size": font_size,
                }
            )

        elif block["type"] == 1:
            if "xref" in block:
                xref = block["xref"]

                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                img_path = save_image(image_bytes, layout)

                page_data["blocks"].append(
                    {
                        "type": "image",
                        "src": img_path,
                        "bbox": block["bbox"],
                    }
                )
            else:
                print(f"⚠️ Skipping image without xref on page {page_index+1}")

    links = page.get_links()
    for link in links:
        if "uri" in link:
            page_data["blocks"].append(
                {
                    "type": "link",
                    "href": link["uri"],
                    "bbox": link.get("from", [0, 0, 0, 0]),
                }
            )

    return page_data


def process_pdf(pdf_path: str, layout: OutputLayout) -> dict:
    ensure_layout_dirs(layout)
    doc = fitz.open(pdf_path)

    document = {
        "title": os.path.basename(pdf_path),
        "pages": [],
    }

    for i, page in enumerate(doc):
        print(f"Processing page {i+1}")
        page_data = process_page(doc, page, i, layout)
        document["pages"].append(page_data)

    return document


RESERVED_DOC_IDS = frozenset(
    {"intro", "img", "assets", "category", "tags", "search", "404"}
)


def _slug_segment(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", label.strip()).strip("-").lower()
    return (s[:200] if s else "")


def _stem_matching_docusaurus_default_id(title: str, page_number: int) -> str:
    """
    Docusaurus treats a leading ``NN-`` on Markdown file names as an ordering
    prefix and strips it when computing the default document id. If we keep
    the raw slug (e.g. ``2-background``), sidebar ids no longer match
    (Docusaurus uses ``document/background``). Apply the same stripping here.
    """
    base = _slug_segment(title) or f"section-{page_number}"
    base = base[:80].rstrip("-") or f"section-{page_number}"
    stem = base
    while True:
        stripped = re.sub(r"^\d+-", "", stem).strip("-")
        if not stripped:
            return f"section-{page_number}"
        if stripped == stem:
            break
        stem = stripped
    if stem[0].isdigit():
        return f"page-{page_number}"
    return stem


def infer_title_from_markdown(md: str, page_number: int) -> str:
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("# ") and len(s) > 2:
            return s[2:].strip()[:200]
        if s.startswith("## ") and len(s) > 3:
            return s[3:].strip()[:200]
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("!["):
            continue
        return s[:200].strip()
    return f"Section {page_number}"


def _allocate_doc_id(title: str, page_number: int, used_ids: set[str]) -> str:
    base = _stem_matching_docusaurus_default_id(title, page_number)
    candidate = base
    n = 2
    while candidate in used_ids or not candidate:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def blocks_to_markdown(page):
    blocks = page["blocks"]

    blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

    lines = group_lines(blocks)

    md = ""

    for line in lines:
        if all(b["type"] == "image" for b in line):
            for b in line:
                md += f"\n![Image]({b['src']})\n"
            continue

        text = merge_line(line)

        if not text:
            continue

        if len(text) < 50:
            md += f"\n## {text}\n"
        else:
            md += f"\n{text}\n"

    return md


def export_markdown_pages(document: dict, layout: OutputLayout) -> list[dict]:
    """
    Write one Markdown file per page. File names and Docusaurus doc ids are derived
    from the first suitable heading or paragraph in the page body. Sidebar order
    follows PDF page order (assigned later with ``sidebar_position`` in the pipeline).
    """
    ensure_layout_dirs(layout)
    used_ids: set[str] = set(RESERVED_DOC_IDS)
    manifest: list[dict] = []
    for page in document["pages"]:
        n = page["page_number"]
        md = blocks_to_markdown(page)
        title = infer_title_from_markdown(md, n)
        doc_id = _allocate_doc_id(title, n, used_ids)
        used_ids.add(doc_id)
        path = os.path.join(layout.pages, f"{doc_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        manifest.append({"doc_id": doc_id, "title": title, "page_number": n})
    print("✅ Markdown exported")
    return manifest


if __name__ == "__main__":
    default_layout = OutputLayout(os.path.join(os.path.dirname(__file__), "output_files"))
    pdf_file = os.path.join(os.path.dirname(__file__), "input_files", "text.pdf")
    document = process_pdf(pdf_file, default_layout)
    pages_meta = export_markdown_pages(document, default_layout)
    print("\n✅ DONE")
    print("📁 Output:")
    print("- output/pages/")
    print("- output/images/")
    for row in pages_meta:
        print(f"  - {row['doc_id']}: {row['title']!r}")
