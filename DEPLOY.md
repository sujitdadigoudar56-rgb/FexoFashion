# Deploying fexo-backend

## Scope: backend only

This covers the **backend only**. The frontend (templates + static
assets, separate `FexoFashion-Frontend` repo) is deployed independently —
on Vercel, later — and is deliberately **not** part of this Docker image
or this deploy pipeline. Until the two are wired together at runtime,
storefront pages that render frontend templates will error (`TemplateDoesNotExist`);
`/admin/` and `/healthz/` don't depend on the frontend and work fine on
their own.

## Why not Vercel for the backend

Vercel deploys serverless functions, not Docker containers — there's no
"run this Dockerfile" option there. This Django app also needs a
persistent process (gunicorn) and local disk for `media/` uploads, neither
of which fit Vercel's model well. So the backend is containerized with
Docker and deployed to **Render**, which runs the Dockerfile directly and
auto-deploys on every push to `main`.

## Repo layout

```
FexoFashion/            <- this repo (git)
└── backend/              <- Django app — self-contained Docker build context
    ├── Dockerfile
    ├── docker-entrypoint.sh
    ├── requirements.txt
    └── .env              <- real secrets, gitignored, create from .env.example
docker-compose.yml         <- local dev, builds the same image Render uses
render.yaml                <- Render Blueprint (Infrastructure-as-code)
.github/workflows/ci.yml
```

## First-time local setup

```bash
cd FexoFashion/backend
cp .env.example .env     # if you don't already have one; fill in real values
```

`backend/.env` needs at minimum: `SECRET_KEY`, `DB_NAME`, `DB_USER`,
`DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSLMODE` (already set up for Neon
Postgres — see the note on rotating credentials below).

## Running locally with Docker

```bash
cd FexoFashion
docker compose up --build
```

- Admin: http://localhost:8000/admin/
- Health check: http://localhost:8000/healthz/
- Storefront (`/`, `/shop/`, etc.): will 500 until a `frontend/` checkout
  exists and `FRONTEND_DIR` points at it — see backend/README.md if you
  want that locally in the meantime.

This builds the exact same image Render builds in production (same
`Dockerfile`, same entrypoint: migrate → collectstatic → gunicorn). Source
is bind-mounted, so code edits show up without a rebuild; a plain restart
(`docker compose restart web`) re-runs migrate/collectstatic.

No local Postgres container is included — `backend/.env` already points
at your Neon database, which is reachable from anywhere with internet
access, including inside the container.

## Deploying to Render (one-time setup)

1. Push this repo to GitHub (`render.yaml` already points at
   `sujitdadigoudar56-rgb/FexoFashion.git` / `main` — update those two
   fields in `render.yaml` first if that's wrong).
2. In the [Render dashboard](https://dashboard.render.com/): **New +** →
   **Blueprint** → select this repo. Render reads `render.yaml` and
   creates the `fexo-backend` web service from it.
3. Render will prompt for the env vars marked `sync: false` in
   `render.yaml` — fill in your **Neon** `DB_NAME`, `DB_USER`,
   `DB_PASSWORD`, `DB_HOST` there (not in the repo).
4. Deploy. After the first successful deploy, note the assigned URL
   (`https://fexo-backend.onrender.com` or your custom domain) and, if it
   differs from the placeholder in `render.yaml`, update `ALLOWED_HOSTS`
   and `CSRF_TRUSTED_ORIGINS` in the Render dashboard (or in `render.yaml`
   and push) to match.

**Cost note:** the Blueprint uses `plan: starter` (paid) and attaches a
1GB persistent disk for `media/`. Render's free tier doesn't support
persistent disks and spins services down when idle, which would both lose
uploaded media and add cold-start latency — not appropriate for this app
as configured. Adjust `plan`/`disk` in `render.yaml` if you want different
sizing.

## Auto-deploy on every push

This is native to Render, not GitHub Actions: once the Blueprint above is
connected, **every push to `main` triggers a new build + deploy**
automatically (`autoDeploy: true` in `render.yaml`). `.github/workflows/ci.yml`
runs in parallel as a sanity check (Django `check --deploy` + a real
`docker build`) but doesn't itself deploy anything — Render's GitHub
integration does.

## Known limitation: media uploads and horizontal scaling

`media/` is stored on a Render persistent disk mounted into the
container. This works for a single instance but does **not** support
scaling to multiple instances (a disk can only attach to one instance).
If/when this needs to scale, move `MEDIA` storage to S3-compatible object
storage (e.g. Cloudflare R2, AWS S3) via `django-storages` — flag if/when
you want that wired up.

## Frontend: separate deploy, wiring up later

`frontend/` today is **server-rendered Django templates** (`{% %}` tags,
no build step, no standalone dev server) — it cannot run on its own or
deploy to Vercel as-is. Deploying it there means turning this backend
into a JSON API and building an actual separate frontend app (e.g.
Next.js) against it — a real architecture change, not a config change.
Flag it when you're ready to tackle that; for now this backend deploy
stands alone.

## Outstanding: rotate leaked credentials

Independent of all the above — `backend/.env`'s Neon `DB_PASSWORD` and
Django `SECRET_KEY` were previously committed to this repo's git history
at the wrong path (`.env` at repo root, now fixed to `backend/.env` and
gitignored — see conversation/commit for details). Rotate both in the
Neon console / by generating a new `SECRET_KEY` before treating this as
production-ready, since the repo is publicly cloneable and the old values
are still visible in history.
