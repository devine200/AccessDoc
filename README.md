# AccessDocs Pilot (demo)

Centralized publishing flow: upload a PDF, extract text (with OCR fallback), generate Markdown with **titles and file names derived from page content**, sync into the **single** Docusaurus project at `demo_docs/` (replacing all docs there), run **`npm run build`**, then copy the resulting `demo_docs/build/` tree to **`backend/templates/doc_builds/<PublishedItem UUID>/`** (one folder per upload, named after the row’s id) and serve it at **`/viewer/<uuid>/`** (or your `DOCUSAURUS_BASE_URL` prefix). Read-only metadata is available over HTTP. Storage is treated as **budgeted and renewable**; this repo does not claim permanence.

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | Django app, REST API, staff upload UI, Celery tasks; viewer routes under `/viewer/<uuid>/` |
| `demo_docs/` | **Only** Docusaurus builder: pipeline replaces `docs/`, `sidebars.ts`, and `static/img/publish/` on each publish, then builds here |
| `backend/utils/` | PDF processing (`main.py`), publish pipeline (`pipeline.py`), plus `input_files/` fixtures |
| `backend/templates/doc_builds/<uuid>/` | Snapshot of `demo_docs/build/` per upload (`<uuid>` = `PublishedItem.pk`; contents gitignored) |

Doc structure inside `demo_docs/docs/`: **`intro.md`** (overview) and a **`document/`** category (**Pages from source**) containing one page per PDF page in order, with optional category index.

## Prerequisites

- **Python** 3.11+ (3.13 works if your stack matches)
- **Node.js** 20+ and **npm** (`npm run build` in `demo_docs/` from the worker; run `npm install` there once after clone)
- **Redis** (Celery broker and result backend by default)
- **Tesseract** (optional but recommended if PDFs need OCR; same as `backend/utils/` usage)
- **PyMuPDF / Fitz** and **Pillow** (installed via `backend/requirements.txt`)

## Backend setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional; defaults work for local dev
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
# non-interactive (e.g. scripts): DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=admin@localhost DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser --noinput
```

### Environment variables

See `backend/.env.example`. Common values:

- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — default `redis://127.0.0.1:6379/0`
- `DOCUSAURUS_BASE_URL` — default `/viewer/`; each snapshot is served at `{DOCUSAURUS_BASE_URL}<uuid>/` with matching `baseUrl` at build time (`/viewer/<uuid>/`).
- `ACCESSDOC_DOCUSAURUS_ROOT` — Docusaurus project path (default: repo `demo_docs/`)
- `ACCESSDOC_DOCUSAURUS_BUILDS_ROOT` — where `build/` snapshots are stored (default: `backend/templates/doc_builds/`)
- `ACCESSDOC_REPO_ROOT` — override if the repo is not the parent of `backend/`
- `ACCESSDOC_MAX_UPLOAD_MB` — default `25`

## Docusaurus (`demo_docs`)

Install dependencies once:

```bash
cd demo_docs
npm install
```

Smoke-build (optional):

```bash
DOCUSAURUS_BASE_URL=/viewer/00000000-0000-4000-8000-000000000000/ DOCUSAURUS_SITE_TITLE="Smoke test" npm run build
```

The upload pipeline runs `npm run build` in `demo_docs/` after writing docs. **Do not run two publishes concurrently** against the same `demo_docs/` tree without an external lock—they share the same `docs/` working directory.

## Running the full stack locally

**1. Redis**

```bash
redis-server
# or: docker run --rm -p 6379:6379 redis:7
```

**2. Celery worker** (must see `node` and `npm` on `PATH` when processing uploads)

Run this from the **`backend/`** directory so Python can import the `accessdoc` package.

```bash
cd backend
source .venv/bin/activate
celery -A accessdoc worker -l info
```

**3. Django**

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

**4. Use the app**

- Public home: `http://127.0.0.1:8000/`
- Staff sign-in (web app): `http://127.0.0.1:8000/login/`
- Django admin: `http://127.0.0.1:8000/admin/login/`
- Upload (staff): `http://127.0.0.1:8000/upload/`
- Dashboard (staff): `http://127.0.0.1:8000/dashboard/` — “Open docs” uses the item’s UUID (same as the API).
- Read-only API (published items only): `http://127.0.0.1:8000/api/items/`
- Viewer: `http://127.0.0.1:8000/viewer/<item-uuid>/docs/intro/`

## Docker (Gunicorn)

Build context is the **repository root**. The image installs **`demo_docs`** npm dependencies (`npm ci`), **`backend`** Python dependencies, runs **`collectstatic`**, then starts **Gunicorn** on port **8000**.

```bash
# From repo root — set DJANGO_SECRET_KEY in the environment or a .env file next to compose
export DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
docker compose up --build
# http://127.0.0.1:8000/ — entrypoint runs createsuperuser --noinput (admin / admin) unless SKIP_DEFAULT_SUPERUSER=1
```

Named volumes keep **`media/`** uploads and **`templates/doc_builds/`** across restarts. SQLite lives in the container layer unless you bind-mount `backend/db.sqlite3`.

Optional **Celery + Redis** (same image, worker runs from `/app/backend`):

```bash
docker compose -f docker-compose.yml -f docker-compose.celery.yml up --build
```

## Backend tests

```bash
cd backend
source .venv/bin/activate
python manage.py test items
```

## Troubleshooting

- **Upload stuck on “Pending”:** With `DEBUG=true`, PDF jobs often run in a **background thread**. Use `ACCESSDOC_USE_CELERY=true` and a Celery worker from **`backend/`** with Redis.
- **Build fails inside the task:** From `demo_docs/`, run `npm install` and `npm run build` manually to capture errors; use Node 20+.
- **Viewer 404 or broken styling:** The snapshot must be built with `DOCUSAURUS_BASE_URL=/viewer/<that-item’s-uuid>/`. The task sets this automatically.
- **Concurrent uploads:** Serialized processing for `demo_docs/` is recommended; overlapping jobs can overwrite each other’s staged docs before build.
