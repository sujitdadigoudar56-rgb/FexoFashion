# FEXO — Backend

Django backend for the FEXO storefront (PostgreSQL, no REST framework —
pure server-rendered Django).

This repo does **not** contain the frontend (templates/CSS/JS). That lives
in a separate repo — see [Frontend checkout](#frontend-checkout) below for
how the two are wired together.

## What's included

- **8 Django apps**: `core`, `accounts`, `categories`, `products`, `cart`, `orders`, `wishlist`, `website`
- **Full storefront**: home, shop with filters (category/color/size/price/search/sort), product detail with image gallery/zoom/360-viewer hook, cart, coupon-aware checkout with GST + shipping calculation, Cash on Delivery orders
- **Accounts**: register, login, password reset (console email backend), dashboard, profile, order history, multi-address book
- **Wishlist**, product reviews & ratings, recently-viewed (session-based), rule-based "Complete the Look" and related products
- **Content**: journal/blog, FAQ, testimonials, Instagram gallery block, newsletter signup, contact form, legal pages (privacy, terms, shipping, returns)
- **Site name and tagline ("Live in Fashion") are admin-editable** — go to `/admin/` → Site Settings to change them anywhere on the site without touching code.

## Admin — full site control

The admin is deliberately kept **separate from customer accounts** — it lives at its own URL with its own custom-branded login page (not shared with the storefront's `/accounts/login/`):

- **URL**: `http://127.0.0.1:8000/admin/`
- **Login**: whatever username/password you set with `python manage.py createsuperuser`
- **Dashboard**: shows live stats (published products, total orders, revenue, registered customers) above the standard model list
- **Everything is manageable from there**: products, variants, stock, images, categories, collections, orders, coupons, customer addresses, reviews, banners, testimonials, Instagram gallery, blog posts, FAQs, contact messages, newsletter subscribers, and site settings (name/tagline/contact info)

## Not included / next steps

This is a strong, fully-working foundation — not the entire 20+ app spec in one shot. Left for a follow-up pass:
- Invoice PDF generation
- Custom admin analytics charts (stock Django admin covers CRUD today)
- Sitemap.xml / robots.txt / schema.org markup
- Real 360°-viewer image sets and product photography (seeded products have no images — see below)
- Coupon management UI beyond the admin panel

## Frontend checkout

`settings.py` reads templates and static assets from `FRONTEND_DIR`
(default: a sibling `../frontend` folder), **not** from inside this repo.
Clone both repos side by side so the default just works:

```
workspace/
├── backend/   <- this repo
└── frontend/  <- the frontend repo (templates/ + static/)
```

If your checkout lives somewhere else, set `FRONTEND_DIR=/absolute/path`
in `.env` — see `.env.example`.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env          # then edit .env — at minimum set a real SECRET_KEY

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_data   # optional: adds sample categories/products/testimonials/FAQs
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
| `FRONTEND_DIR` | Absolute path to the frontend repo checkout | unset → defaults to sibling `../frontend` |

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

Visit `http://127.0.0.1:8000/` for the storefront and `http://127.0.0.1:8000/admin/` for the dashboard.

### Adding product photos

The seed command creates products **without images** (no real photography ships in this repo). Upload images per product from `/admin/` → Products → open a product → add images in the inline "Product images" section, or add images to `Category`/`Banner`/`BlogPost` the same way. Until then, the UI shows tasteful placeholder imagery so pages never break.

## Notes

- Payment method is Cash on Delivery only, as specified.
- GST is configurable per-product (`gst_percent`, defaults to 5%).
- Free shipping automatically applies above ₹2,999; otherwise a flat ₹149 fee.
- Emails (password reset, etc.) print to the console in development — check your terminal.
