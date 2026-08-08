# FEXO — Frontend

Templates and static assets for the FEXO storefront: light, minimal
Zara/Snitch-style design (white/off-white with dark text), GSAP scroll
reveals + Lenis smooth scroll + magnetic buttons + animated loader, fully
responsive. The homepage hero keeps a full-bleed dark-overlay image for
contrast, matching how those sites treat hero banners — everything else
on the site is light.

```
frontend/
├── templates/     # Django templates (server-rendered)
│   ├── accounts/ cart/ orders/ products/ website/ wishlist/ admin/
│   └── base.html
└── static/
    ├── css/fexo.css
    └── js/fexo.js  # vanilla JS + GSAP/Lenis, no build step, no bundler
```

## Important: this is not a standalone app

There's **no build step, no dev server, no `package.json`** here — these
templates use Django's template language (`{% %}` / `{{ }}` tags) and are
rendered server-side by the [backend](../backend) repo. This repo can't
run or be previewed on its own; it needs the backend process to render
and serve it.

To see it working, clone the [backend repo](../backend) alongside this
one and follow its README:

```
workspace/
├── backend/   <- Django app, run this
└── frontend/  <- this repo, consumed by the backend
```

By default the backend looks for a sibling `../frontend` folder (override
via `FRONTEND_DIR` in the backend's `.env` if your checkout differs).

## Editing templates/assets

- Templates use standard Django template inheritance — `base.html` is the
  shared shell; page templates `{% extends "base.html" %}`.
- Context variables available in templates come from the backend's views
  and context processors (cart summary, wishlist summary, nav categories,
  site settings, admin dashboard stats) — check the backend repo's
  `context_processors.py` files in each app to see what's available
  globally vs. per-view.
- `static/css/fexo.css` and `static/js/fexo.js` are hand-written, no
  preprocessor/bundler — edit directly and reload.
