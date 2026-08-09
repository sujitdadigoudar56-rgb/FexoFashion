# FEXO — Live in Fashion

A luxury fashion e-commerce platform built with Django (PostgreSQL, no
REST framework, no Node.js — pure Django + vanilla JS/GSAP/Lenis).

This workspace holds **two independent git repos**, kept side by side so
the backend can find the frontend at its default relative path:

```
fexo123/            <- plain folder, not a git repo itself
├── backend/          <- git repo: Django app, settings, manage.py, DB config
└── frontend/          <- git repo: templates + static assets, no Python
```

Each repo has its own README with full setup instructions:

- **[backend/README.md](backend/README.md)** — Django setup, `.env`,
  PostgreSQL, admin, running the server. Start here.
- **[frontend/README.md](frontend/README.md)** — what's in the templates
  and static assets, how they're consumed by the backend (there's no
  build step or standalone way to run this repo). Deployed separately
  (e.g. Vercel) — not part of the backend's Docker/Render deploy.
- **[DEPLOY.md](DEPLOY.md)** — Docker + Render production deploy for the
  **backend only** (auto-deploys on every push to `main`).

## Quick start

```bash
# both repos already exist locally as siblings — see backend/README.md
# for the full setup (venv, .env, PostgreSQL, migrations, seed data)
cd backend
source ../venv/bin/activate
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the storefront and
`http://127.0.0.1:8000/admin/` for the dashboard.
# fexo-project
