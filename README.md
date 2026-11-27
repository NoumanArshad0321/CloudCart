# CloudCart — Cloud-Based E-Commerce Product Image Storage System

A university Cloud Computing lab project. The app is hosted in the
cloud on **Render** (free tier): anyone with the link can open it,
and it does not depend on the owner's laptop being on. Product
images are stored on the server's disk (`instance/uploads/`), and
product information lives in SQLite — the database only ever stores
the image's file name, never the image itself.

> **Honest limit, up front:** on Render's free tier the server's
> disk is **ephemeral** — uploaded images and the SQLite database
> can be lost when Render restarts or redeploys the service. The
> deployed demo is disposable: re-add products after a restart. A
> production setup would use object storage instead; see
> `docs/RENDER_STORAGE.md`.

## Problem statement

A small online shop needs product photos that customers can see from
anywhere. If the shop only runs on the owner's laptop, it disappears
when the laptop is off or lost, and nobody else can reach it.
CloudCart moves the whole application into the cloud — hosted on
Render — so it is available anywhere, while keeping the design simple
enough for a lab: images on the server's disk, data in SQLite.

## Objectives

1. Let users add, view, search, filter and delete products.
2. Store product images on the server's disk with unique file names.
3. Store product information in SQLite (never image files in the database).
4. Show the real deployment status — never fake it.
5. Run honestly on a local computer before it is deployed (Local Mode).
6. Deploy for free on Render, with the free tier's limits stated plainly.

## Features

- **Dashboard** — total products, images stored, total and average
  image size, recent uploads, gallery preview. All numbers are
  calculated from the real database.
- **Products** — cards with image, name, price in PKR, category, image
  size, storage location, View details, Delete. Search by name, filter
  by category.
- **Add Product** — name, price, category, description, image upload
  with live preview. Only JPG/JPEG/PNG/WebP, max 5 MB.
- **Product detail** — the whole product, large, with file name, size
  and storage location.
- **Cloud Storage** — how storage really works, where the app is
  running (Render or Local Mode), and the ephemeral-disk limit.
- **About** — why Render is used, and local computer vs cloud hosting.
- **Security** — CSRF protection, server-side validation, safe
  filenames, unique file names, environment-based secrets, and
  deletion that only ever removes the file named in that product's
  own row.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5, vanilla JavaScript |
| Backend | Python 3.12, Flask 3.0.3 |
| Database | SQLite (created automatically on startup) |
| Image storage | Server disk, `instance/uploads/`, unique UUID file names |
| Production server | Gunicorn |
| Testing | pytest |
| Hosting | Render (free tier) |

Exact pinned versions are in `requirements.txt` and were verified to
install and run together on Python 3.12.3:
Flask 3.0.3, Flask-WTF 1.2.1, WTForms 3.1.2, python-dotenv 1.0.1,
gunicorn 22.0.0, pytest 8.3.2.

## Architecture

```
Browser ──► Flask on Render (app.py) ──► SQLite (instance/cloudcart.db)
              │                              (product info only)
              ▼
        Server disk: instance/uploads/
              (image files only, UUID names)
```

When run **locally**, the same design runs on your own computer:
Flask + SQLite + `instance/uploads/` on your disk, and the sidebar
honestly says "Local Mode".

## Folder structure

```
CloudCart/
├── app.py                 Flask app (run this)
├── config.py              Settings from environment variables
├── storage.py             Disk image storage (UUID names, safe delete)
├── database.py            SQLite: create table, CRUD, search, stats
├── requirements.txt       Pinned dependencies
├── Procfile               web: gunicorn app:app
├── render.yaml            Render Blueprint (free web service "cloudcart")
├── runtime.txt            python-3.12.3
├── .env.example           Copy to .env and fill in your SECRET_KEY
├── .gitignore             Keeps .env and the database out of git
├── templates/             HTML pages (base, dashboard, products, ...)
├── static/css/style.css   Dashboard styling
├── static/js/app.js       Image preview + 5 MB check
├── tests/test_app.py       pytest tests
└── docs/                  RENDER_STORAGE.md, DEPLOYMENT.md, LAB_REPORT.md
```

## Installation (Windows PowerShell)

```powershell
cd Desktop\CloudCart
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env in Notepad and add your SECRET_KEY.
python app.py
```

On Mac / Linux, use `python3 -m venv venv`, `source venv/bin/activate`,
and `cp .env.example .env` instead.

Then open **http://127.0.0.1:5000**.

## Environment variables

| Variable | Required | What it is |
|---|---|---|
| `SECRET_KEY` | Yes | A long random string for sessions/CSRF. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

That is the only secret. Render sets `RENDER=true` itself — the app
reads it to know it is really running on Render.

## Database setup

None needed by hand. The SQLite file `instance/cloudcart.db` is created
automatically the first time the app starts.

## Running locally

```bash
python app.py
```

## Testing

```bash
pytest -v
```

Covered: dashboard/products/cloud-storage/about pages load; Cloud
Storage page explains Render and the ephemeral-disk limit; empty name,
negative price, unsupported image type and oversized image are all
rejected; add/list/search/filter/detail/delete all work; uploading
saves a file with a UUID name; deleting removes the database row and
the image file; the image route rejects bad filenames; storage unit
tests prove the UUID naming and safe delete.

**Not yet verified:** the Render deployment. It needs the user's
GitHub/Render login, which was not provided. See
`docs/DEPLOYMENT.md` for the exact next steps.

## Deployment on Render

Free tier (as stated in the project brief, to be re-checked on Render's
own pricing page at deployment time): 750 instance-hours per workspace
per month, 512 MB RAM, no credit card required, services spin down
after 15 minutes without traffic (about a 1-minute cold start), and an
ephemeral filesystem with no persistent disk on the free tier.

Full steps are in `docs/DEPLOYMENT.md`. In short: push this folder to a
GitHub repo named `CloudCart`, create a Web Service from it in Render
(or use the `render.yaml` Blueprint), pick the **Free** instance type,
and set `SECRET_KEY` in the Render dashboard.

## Free-tier limitations (important)

- The free service sleeps after 15 minutes idle; the first visit after
  that takes about a minute.
- The filesystem is ephemeral: **both the SQLite database and the
  uploaded images can be lost on a restart or redeploy**. Treat the
  deployed demo as disposable and re-add products after a restart.
- If the 750 free hours run out, free services are suspended until the
  next month. Do not use uptime-pinging to prevent sleeping.
- Render free needs no card, so it cannot charge you unless you upgrade.
  Never upgrade to a paid plan without a deliberate decision.

## Security

- Secrets live in environment variables / `.env`, never in code or git.
  `.env` and `*.db` are in `.gitignore`.
- Only the file name is stored in SQLite — never the image itself.
- Uploads: JPG/JPEG/PNG/WebP only, max 5 MB, safe filenames, unique
  file names, CSRF protection on every form.
- Images are served only through `/uploads/<filename>`, which rejects
  any name that is not a UUID image name.
- Deletion only ever removes the file named in that product's own
  database row, after checking the name against a safe pattern.
- Errors show friendly pages, never raw stack traces.

## Cost considerations

- Render free tier: no card, no charge unless you upgrade.
- A production setup would add object storage (e.g. Amazon S3, Azure
  Blob Storage, Cloudflare R2) and a hosted database — check current
  pricing first, and never assume any of it is completely free.

## Known limitations

- Render deployment is not yet verified (see Testing above).
- On Render free tier the SQLite database AND the uploaded images are
  ephemeral (see above).
- Product images are single images per product; there is no multi-image
  gallery or thumbnail generation.
- No user accounts — anyone with the link can add or delete products.
  That is fine for a lab demo, not for a real shop.

## Future improvements

- Move images to object storage (e.g. S3 / Azure Blob / R2) so they
  survive restarts.
- A persistent database (e.g. Render's free PostgreSQL) so products
  survive restarts.
- User accounts and an admin-only Add/Delete.
- Multiple images per product.
- Image thumbnails generated on upload.
- Price history and stock levels.
