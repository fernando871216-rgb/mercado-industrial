# AGENTS.md

## Setup and Environment

This is a Django 6.1.2 application (Python) for "Mercado Industrial INITRE" marketplace.

- **Working directory**: `F:\mercado-industrial`
- **Git repo**: yes (connected to `https://github.com/fernando871216-rgb/mercado-industrial.git`)
- **Settings module**: `industrial_mkt.settings`
- **App module**: `marketplace`
- **.env**: Required for local dev (loaded via `python-dotenv`). Contains `DATABASE_URL`, `DEBUG`, `SECRET_KEY`. Never commit `.env`.

### Python Environment

Use the local virtual environment. Always invoke Python via the venv to ensure dependencies match `requirements.txt`.

```powershell
# Windows (PowerShell)
cd "F:\mercado-industrial"
.\.venv\Scripts\python.exe manage.py check
```

Dependencies: `django`, `mercadopago`, `gunicorn`, `whitenoise`, `psycopg2-binary`, `Pillow`, `dj-database-url`, `cloudinary`, `django-cloudinary-storage`, `requests`, `python-dotenv` (see `requirements.txt`).

## Database & Configuration

- **Database**: Uses `dj_database_url.config()` with fallback to `sqlite:///db.sqlite3`. `.env` is loaded in `industrial_mkt/settings.py` via `load_dotenv()` (HEAD merge keeps this). 
- **Production DB**: Migrated from Render PostgreSQL → Supabase (Transaction Pooler `:6543` with `?sslmode=require`). Production `DATABASE_URL` is set as Render environment variable.
- **Do NOT run `migrate` after `pg_restore`** on production data dumps (schema+data already restored). Only run migrations for new schema changes.
- **Migrations**: `marketplace/migrations/0001_initial.py`, `0002_sale_shipping_cp.py`.

## Development Commands

From `F:\mercado-industrial`:

```powershell
# System check
.\.venv\Scripts\python.exe manage.py check

# Run dev server (default 8000)
.\.venv\Scripts\python.exe manage.py runserver

# Run tests
.\.venv\Scripts\python.exe manage.py test

# Create migrations / apply
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate

# Django shell
.\.venv\Scripts\python.exe manage.py shell
```

## Key Architecture

- **Django project**: `industrial_mkt/` (settings, urls, wsgi, asgi, sitemaps)
- **Core app**: `marketplace/` (models, views, urls, forms, utils, admin, templatetags)
- **Models (key)**: `Category`, `IndustrialProduct`, `Profile`, `Sale`. Note: model is `IndustrialProduct` (not `Product`).
- **Static**: `static/` + `STATICFILES_STORAGE = whitenoise.storage.CompressedManifestStaticFilesStorage`
- **Media/files**: Cloudinary via `django-cloudinary-storage` (images + raw/PDFs). Cloudinary config present in settings.
- **Payments**: MercadoPago integration (`mercadopago`).
- **Emails**: SMTP via Gmail (uses `EMAIL_HOST_PASSWORD` from env).
- **Templates**: `marketplace/templates/`, includes auth/registration and emails.

## Android App (WebView)

Located at `C:\Users\inies\AndroidStudioProjects\MercadoIndustrial/` (separate from backend). MainActivity loads the web app:

```java
myWebView.loadUrl("https://mercado-industrial.onrender.com");
```

**Important**: Changing backend DB to Supabase does not require recompiling Android if it still points to Render (Render proxies to Supabase). Only update/rebuild Android if you change that URL.

## Git & Workflow Notes

- Repo: `fernando871216-rgb/mercado-industrial.git` (private). `.git` present in `F:\mercado-industrial`.
- After pulling remote with different history, use `--allow-unrelated-histories` if needed; resolve conflicts and commit.
- Working tree clean at HEAD `7cb0ea6`. `.env` is local-only (never committed).
- Large media: `static/app_initre.apk`, `video_promo_initre.mp4` tracked.

## Operational Gotchas

- **Virtualenv required**: `ModuleNotFoundError: No module named 'django'` means not using `.venv\Scripts\python.exe`.
- **python-dotenv required**: `.env` only loaded if `load_dotenv()` runs (present in HEAD). Install `python-dotenv` in venv if missing.
- **psycopg**: Use `psycopg2-binary` (as in requirements). For Supabase use Transaction Pooler port `6543` + `sslmode=require`.
- **Cloudinary raw files**: Uses `RawMediaCloudinaryStorage` for technical sheets (`ficha_tecnica`).
- **Repo has merge conflict markers** in some files (e.g. `requirements.txt`, `manage.py`, `settings.py`) from prior merge — current files on disk reflect resolved/merged state; be careful not to reintroduce `<<<<<<<` markers.
- **Do not overwrite production data carelessly**: `pg_restore --clean` drops/creates objects; only use against intended target DB.
- **Render DB backup**: Keep `mercado_industrial.dump` as safety backup before deleting Render DB.
- **Windows shell**: PowerShell; prefer venv python paths over global `python`.

## Quick Verification

```powershell
cd "F:\mercado-industrial"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

Both should pass cleanly before making changes.