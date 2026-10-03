# FEXO — Backend

Django + Django REST Framework backend for the FEXO storefront
(PostgreSQL). Django renders no pages: the storefront is a separate
[Next.js frontend](#frontend) and the admin is a separate Next.js app
(Fexo-admin). Both consume this project's JSON API, mounted under `/api/`.

## What's included

- **9 Django apps**: `core`, `accounts`, `categories`, `products`, `cart`, `orders`, `wishlist`, `website`, `dashboard` (staff admin API)
- **REST API** (`/api/...`, DRF + Token authentication + `django-cors-headers`): products with filters (category/collection/color/size/price/search/sort) + pagination, categories/collections, server-persisted cart (authenticated), coupon-aware checkout with GST + shipping calculation, Cash on Delivery orders, wishlist, product reviews & ratings, "Complete the Look"/related products
- **Accounts API**: register, login/logout (token), password reset (console email backend, link points at the frontend's confirm page), profile, order history, multi-address book
- **Content API**: journal/blog, FAQ, testimonials, Instagram gallery block, newsletter signup, contact form, site settings
- **Site name and tagline ("Live in Fashion") are admin-editable** — go to the admin app → Site settings, exposed to the frontend via `GET /api/site-settings/`.

## Admin — full site control

Django's built-in `django.contrib.admin` UI has been removed. Store
administration lives in the separate **Fexo-admin** Next.js app, backed by the
staff-only API in the `dashboard` app:

- **API**: `/api/admin/...`. Every endpoint requires an active `is_staff` user's DRF token.
- **Login**: `POST /api/admin/auth/login/ {email, password}` accepts an email or username and rejects non-staff accounts. Create the first admin with `python manage.py createsuperuser` (or the `DJANGO_SUPERUSER_*` env vars used by `ensure_superuser`).
- **Covers**: dashboard stats (`/stats/`), products, images, per-size stock, categories, collections, reviews, orders (status/notes), customers (activate, grant admin), coupons, banners, testimonials, Instagram, journal, FAQs, contact messages, newsletter subscribers (+ CSV export), and site settings.
- **CORS**: add the admin app's origin (e.g. `http://localhost:3001`) to `CORS_ALLOWED_ORIGINS`.

## Not included / next steps

This is a strong, fully-working foundation — not the entire 20+ app spec in one shot. Left for a follow-up pass:
- Invoice PDF generation
- Sitemap.xml / robots.txt / schema.org markup
- Real 360°-viewer image sets (seed data ships plain placeholder photography — see below)
- Guest (unauthenticated) cart — cart/wishlist/orders are all authenticated-only in this API; there's no anonymous-session cart the way a fully server-rendered app would have

## Frontend

The storefront is a separate Next.js app —
`Fexo_Frontend/FexoFashion-Frontend` — that talks to this project purely
over the JSON API mounted under `/api/`. Two settings connect them (see
`.env.example`):

- `CORS_ALLOWED_ORIGINS` — origins allowed to call the API from a browser (default `http://localhost:3000`)
- `FRONTEND_URL` — used to build the password-reset confirmation link the frontend renders (default `http://localhost:3000`)

Run both locally side by side: this project on `:8000`, the frontend's
`npm run dev` on `:3000` (with its own `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
in `.env.local`).

## Setup

```bash
python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env          # then edit .env — at minimum set a real SECRET_KEY

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_data   # adds sample categories/products (+ placeholder photos)/testimonials/FAQs/coupons/journal posts
python manage.py runserver
```

### Environment variables (`.env`)

Config that differs per environment (or shouldn't be committed) is read
from `.env` via `python-dotenv`, not hardcoded in `settings.py`.
See `.env.example` for the full list:

| Variable | Purpose | Local default |
|---|---|---|
| `SECRET_KEY` | Django's cryptographic signing key | dev-only fallback baked into settings.py if unset — **replace it for anything beyond local dev** |
| `DEBUG` | `True`/`False` | `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames allowed to serve the app | `localhost,127.0.0.1` |
| `DB_NAME` | PostgreSQL database name | `fexo_db` |
| `DB_USER` | PostgreSQL role | `fexo_user` |
| `DB_PASSWORD` | PostgreSQL role password | — (required) |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call `/api/` from a browser | `http://localhost:3000` |
| `FRONTEND_URL` | Base URL of the Next.js frontend, used in password-reset emails | `http://localhost:3000` |

### Database (PostgreSQL)

The project runs on PostgreSQL — SQLite is no longer used. One-time local
setup, assuming PostgreSQL is already installed and running:

```bash
psql -U <your-superuser> -d postgres <<SQL
CREATE ROLE fexo_user WITH LOGIN PASSWORD 'change-me';
CREATE DATABASE fexo_db OWNER fexo_user;
GRANT ALL PRIVILEGES ON DATABASE fexo_db TO fexo_user;
SQL
```

Then set `DB_PASSWORD` in `.env` to match, and run `python manage.py
migrate` as usual — Django creates all tables in `fexo_db`. `pip install
-r requirements.txt` already pulls in `psycopg2-binary`, the Postgres
driver.

Run the storefront (Fexo-Frontend, port 3000) and the admin app (Fexo-admin, port 3001) against this API.

### Running with Docker instead

`docker compose up --build` from the repo root builds and runs this app
in the same container image used in production. See
[../DEPLOY.md](../DEPLOY.md) for that, plus the Render deployment setup
(auto-deploys on every push to `main`).

### Adding product photos

`seed_demo_data` generates plain solid-color placeholder JPEGs (via
Pillow) for every product/category/banner/journal post it creates — no
real photography ships in this repo. Replace them any time by uploading
real images per product from the admin app → Products → open a product → the
inline "Product images" section (same for `Category`/`Banner`/
`BlogPost`). The frontend also falls back to a placehold.co image for
anything left with no image at all, so pages never break either way.

## Notes

- Payment method is Cash on Delivery only, as specified.
- GST is configurable per-product (`gst_percent`, defaults to 5%).
- Free shipping automatically applies above ₹2,999; otherwise a flat ₹149 fee.
- Emails (password reset, etc.) print to the console in development — check your terminal.
- API auth is DRF Token authentication — the frontend sends `Authorization: Token <t>` (obtained from `POST /api/accounts/login/` or `/register/`), not session cookies. `SessionAuthentication` is also enabled for DRF's browsable API while developing.
