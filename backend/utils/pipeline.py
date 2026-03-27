"""
Publish flow: one shared Docusaurus project at ``demo_docs``.

Each run replaces ``demo_docs/docs`` and ``static/img/publish``, runs ``npm run build``
there with ``DOCUSAURUS_BASE_URL=/viewer/<item_uuid>/``, then copies ``demo_docs/build/``
to ``DOCUSAURUS_BUILDS_ROOT/<upload_uuid>/`` (folder name = ``PublishedItem.pk``) for Django.

Only one publish should run at a time against ``demo_docs`` (shared working tree).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .main import OutputLayout, export_markdown_pages, process_pdf

DOC_SUBDIR = "document"
IMG_PUBLISH_DIR = "publish"


def _write_sidebars(site: Path, document_item_ids: list[str]) -> None:
    if not document_item_ids:
        doc_sidebar_body = "docSidebar: ['intro']"
    else:
        items_js = ",\n      ".join(json.dumps(x) for x in document_item_ids)
        doc_sidebar_body = f"""docSidebar: [
    'intro',
    {{
      type: 'category',
      label: 'Pages from source',
      collapsed: false,
      items: [
      {items_js}
      ],
    }},
  ]"""

    content = f"""import type {{SidebarsConfig}} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {{
  {doc_sidebar_body},
}};

export default sidebars;
"""
    (site / "sidebars.ts").write_text(content, encoding="utf-8")


def _write_intro(
    site_docs: Path, title: str, description: str, *, has_pages: bool
) -> None:
    desc = (description or "").strip()
    body: list[str] = [
        "---",
        "sidebar_position: 1",
        "title: Overview",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if desc:
        body.append(desc)
        body.append("")
    if has_pages:
        body.append(
            "The **Pages from source** section lists each PDF page in order, using titles and "
            "filenames inferred from the page text."
        )
    else:
        body.append("No pages were extracted from this PDF.")
    body.append("")
    (site_docs / "intro.md").write_text("\n".join(body), encoding="utf-8")


def _write_document_category(
    doc_sub: Path, *, doc_title: str, description: str
) -> None:
    desc_text = (description or "").strip() or "Sections extracted from the uploaded PDF."
    category = {
        "label": "Pages from source",
        "position": 2,
        "link": {
            "type": "generated-index",
            "title": f"Pages — {doc_title}"[:120],
            "description": desc_text[:500],
        },
    }
    (doc_sub / "_category_.json").write_text(
        json.dumps(category, indent=2) + "\n", encoding="utf-8"
    )


def _frontmatter(sidebar_position: int, title: str, body: str) -> str:
    return (
        "---\n"
        f"sidebar_position: {sidebar_position}\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        "---\n\n"
        f"{body}"
    )


def _replace_docs_in_demo_site(
    docusaurus_root: Path,
    *,
    title: str,
    description: str,
    layout: OutputLayout,
    pages_meta: list[dict],
) -> None:
    docs_root = docusaurus_root / "docs"
    if docs_root.exists():
        shutil.rmtree(docs_root)
    docs_root.mkdir(parents=True)

    _write_intro(docs_root, title, description, has_pages=bool(pages_meta))

    document_refs: list[str] = []
    if pages_meta:
        doc_sub = docs_root / DOC_SUBDIR
        doc_sub.mkdir(parents=True)
        _write_document_category(doc_sub, doc_title=title, description=description)

        img_prefix = f"/img/{IMG_PUBLISH_DIR}/"
        pages_dir = Path(layout.pages)
        pos = 1
        for row in pages_meta:
            doc_id = row["doc_id"]
            raw = (pages_dir / f"{doc_id}.md").read_text(encoding="utf-8")
            raw = raw.replace("](images/", f"]({img_prefix}")
            doc_title = row["title"]
            fm = _frontmatter(pos, doc_title, raw)
            (doc_sub / f"{doc_id}.md").write_text(fm, encoding="utf-8")
            pos += 1
        document_refs = [f"{DOC_SUBDIR}/{row['doc_id']}" for row in pages_meta]

    _write_sidebars(docusaurus_root, document_refs)

    pub_img = docusaurus_root / "static" / "img" / IMG_PUBLISH_DIR
    if pub_img.exists():
        shutil.rmtree(pub_img)
    pub_img.mkdir(parents=True)
    if Path(layout.images).is_dir():
        for name in os.listdir(layout.images):
            src = Path(layout.images) / name
            if src.is_file():
                shutil.copy2(src, pub_img / name)


def run_npm_build(docusaurus_root: str, env: dict[str, str] | None = None) -> None:
    merged = {**os.environ, **(env or {})}
    subprocess.run(
        ["npm", "run", "build"],
        cwd=docusaurus_root,
        check=True,
        env=merged,
    )


def run_pdf_pipeline(
    pdf_path: str,
    *,
    work_dir: str,
    publish_id: str,
    title: str,
    description: str,
    docusaurus_root: str,
    builds_root: str,
    build_env: dict[str, str] | None = None,
    run_build: bool = True,
) -> dict[str, Any]:
    """
    Extract PDF, replace all docs in ``docusaurus_root``, build once, copy output to
    ``builds_root / publish_id``.
    """
    layout = OutputLayout(os.path.join(work_dir, "extracted"))
    document = process_pdf(pdf_path, layout)
    if title:
        document["title"] = title
    pages_meta = export_markdown_pages(document, layout)

    root = Path(docusaurus_root).resolve()
    _replace_docs_in_demo_site(
        root,
        title=title or document.get("title") or publish_id,
        description=description,
        layout=layout,
        pages_meta=pages_meta,
    )

    out_root = Path(builds_root).resolve() / publish_id
    if run_build:
        if out_root.exists():
            shutil.rmtree(out_root)
        run_npm_build(str(root), env=build_env)
        built = root / "build"
        if not built.is_dir():
            raise RuntimeError(f"Docusaurus build output missing: {built}")
        shutil.copytree(built, out_root)
    else:
        out_root.mkdir(parents=True, exist_ok=True)

    return {
        "publish_id": publish_id,
        "page_count": len(document["pages"]),
        "pages_copied": len(pages_meta),
        "build_dir": str(out_root),
        "docusaurus_root": str(root),
    }
