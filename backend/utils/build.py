"""
Local helper: copy extracted markdown/images into ``demo_docs`` and run ``npm run build``.

Publishing from Django uses ``utils.pipeline.run_pdf_pipeline`` instead.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DOCUSAURUS_PATH = Path(
    os.environ.get("ACCESSDOC_DOCUSAURUS_ROOT", str(_REPO_ROOT / "demo_docs"))
).resolve()

DOCS_PATH = _DOCUSAURUS_PATH / "docs"
STATIC_IMG_PUBLISH = _DOCUSAURUS_PATH / "static" / "img" / "publish"

_UTILS_ROOT = Path(__file__).resolve().parent
LOCAL_OUTPUT = str(_UTILS_ROOT / "output_files")
LOCAL_PAGES = os.path.join(LOCAL_OUTPUT, "pages")
LOCAL_IMAGES = os.path.join(LOCAL_OUTPUT, "images")


def copy_markdown():
    for file in os.listdir(LOCAL_PAGES):
        if file.endswith(".md"):
            src = os.path.join(LOCAL_PAGES, file)
            dest = os.path.join(DOCS_PATH, file)
            shutil.copy(src, dest)
    print("✅ Markdown files copied")


def copy_images():
    os.makedirs(STATIC_IMG_PUBLISH, exist_ok=True)
    for file in os.listdir(LOCAL_IMAGES):
        src = os.path.join(LOCAL_IMAGES, file)
        dest = os.path.join(STATIC_IMG_PUBLISH, file)
        shutil.copy(src, dest)
    print("✅ Images copied")


def fix_image_paths():
    for dirpath, _, files in os.walk(DOCS_PATH):
        for file in files:
            if not file.endswith(".md"):
                continue
            path = Path(dirpath) / file
            content = path.read_text(encoding="utf-8")
            content = content.replace("](images/", "](/img/publish/")
            path.write_text(content, encoding="utf-8")
    print("✅ Image paths fixed")


def build():
    print("⚙️ Running build...")
    subprocess.run(["npm", "run", "build"], cwd=str(_DOCUSAURUS_PATH), check=True)
    print("✅ Build complete")


def publish():
    copy_markdown()
    copy_images()
    fix_image_paths()
    build()


if __name__ == "__main__":
    publish()
