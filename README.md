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
- **PostgreSQL** 14+ (required; SQLite is not supported)
- **Node.js** 20+ and **npm** (`npm run build` in `demo_docs/` from the worker; run `npm install` there once after clone)
- **Redis** (Celery broker and result backend by default)
- **Tesseract** (optional but recommended if PDFs need OCR; same as `backend/utils/` usage)
- **PyMuPDF / Fitz** and **Pillow** (installed via `backend/requirements.txt`)

## Backend setup

Start Postgres (example — adjust user, password, and database name to match `DATABASE_URL`):

```bash
docker run --name accessdoc-pg -e POSTGRES_USER=accessdoc -e POSTGRES_PASSWORD=accessdoc -e POSTGRES_DB=accessdoc -p 5432:5432 -d postgres:16-alpine
```

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL if your Postgres differs
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
# non-interactive (e.g. scripts): DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=admin@localhost DJANGO_SUPERUSER_PASSWORD=admin python manage.py createsuperuser --noinput
```

### Environment variables

See `backend/.env.example`. Common values:

- **`DATABASE_URL`** — required, e.g. `postgresql://accessdoc:accessdoc@127.0.0.1:5432/accessdoc` (Railway/Heroku provide this automatically for managed Postgres)
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

**1. PostgreSQL** — must match `DATABASE_URL` in `.env` (see Backend setup).

**2. Redis**

```bash
redis-server
# or: docker run --rm -p 6379:6379 redis:7
```

**3. Celery worker** (must see `node` and `npm` on `PATH` when processing uploads)

Run this from the **`backend/`** directory so Python can import the `accessdoc` package.

```bash
cd backend
source .venv/bin/activate
celery -A accessdoc worker -l info
```

**4. Django**

```bash
cd backend
source .venv/bin/activate
python manage.py runserver
```

**5. Use the app**

- Public home: `http://127.0.0.1:8000/`
- Staff sign-in (web app): `http://127.0.0.1:8000/login/`
- Django admin: `http://127.0.0.1:8000/admin/login/`
- Upload (staff): `http://127.0.0.1:8000/upload/`
- Dashboard (staff): `http://127.0.0.1:8000/dashboard/` — “Open docs” uses the item’s UUID (same as the API).
- Read-only API (published items only): `http://127.0.0.1:8000/api/items/`
- Viewer: `http://127.0.0.1:8000/viewer/<item-uuid>/docs/intro/`

## Docker (build + web with Gunicorn and Celery)

The **Dockerfile** only **prepares the codebase**: Node 20, **`demo_docs/`** `npm ci`, Python deps, **`collectstatic`**. Nothing long-running is started during the image build except what Django needs for static collection.

**`docker compose up --build`** starts three services from that image:

- **postgres** — PostgreSQL 16; user/password/db **`accessdoc`** (override by changing compose `DATABASE_URL` and `POSTGRES_*` together).
- **redis** — broker and result backend for Celery.
- **web** — migrates, optional default superuser (**admin** / **admin** unless `SKIP_DEFAULT_SUPERUSER=1`), starts **Celery** in the background (`ACCESSDOC_EMBEDDED_CELERY_WORKER=1`), then **Gunicorn** on port **8000** with **`ACCESSDOC_USE_CELERY=true`** so uploads enqueue tasks and the same container consumes them.

Named volumes persist **`postgres_data`** (database), **`media/`**, and **`templates/doc_builds/`** so uploads and builds stay on disk across restarts.

For a **dedicated worker container only** (no HTTP), run the image with **`ACCESSDOC_CONTAINER_ROLE=worker`** (see `docker/entrypoint.sh`). Do not run that **and** **`ACCESSDOC_EMBEDDED_CELERY_WORKER=1`** on separate replicas of the same app, or tasks may be processed twice.

```bash
# From repo root — set DJANGO_SECRET_KEY in the environment or a .env file next to compose
export DJANGO_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
docker compose up --build
# http://127.0.0.1:8000/
```

## Backend tests

Requires a running PostgreSQL instance (Django creates a `test_*` database on the same server). Example:

```bash
# If DATABASE_URL in .env points at localhost:5432
cd backend
source .venv/bin/activate
python manage.py test items
```

## Troubleshooting

- **Upload stuck on “Pending” (production / Celery):** Typical causes: (1) **No worker** — Celery is not running; Docker Compose in this repo runs an **embedded** worker with Gunicorn (`ACCESSDOC_EMBEDDED_CELERY_WORKER=1`). On Railway or a single container, set the same. (2) **Wrong Redis URL** — platforms often set **`REDIS_URL`**; this project falls back to it when **`CELERY_BROKER_URL`** is unset. If both are missing, Django defaults to `127.0.0.1` and task enqueue fails (check server logs for *Failed to queue process_published_item*). (3) **Missing or different `DATABASE_URL`** — every process must use the **same** Postgres. (4) **Split media disk** — if web and worker run on different machines without shared storage, the worker may not see uploaded PDFs under `MEDIA_ROOT`; use shared volumes or a single container with embedded Celery.
- **Upload stuck on “Pending” (local):** With `DEBUG=true`, PDF jobs often run in a **background thread**. Use `ACCESSDOC_USE_CELERY=true` and `celery -A accessdoc worker` with Redis.
- **Build fails inside the task:** From `demo_docs/`, run `npm install` and `npm run build` manually to capture errors; use Node 20+.
- **Viewer 404 or broken styling:** The snapshot must be built with `DOCUSAURUS_BASE_URL=/viewer/<that-item’s-uuid>/`. The task sets this automatically.
- **Concurrent uploads:** Serialized processing for `demo_docs/` is recommended; overlapping jobs can overwrite each other’s staged docs before build.
