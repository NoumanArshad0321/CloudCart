# Lab Report — CloudCart: Cloud-Based E-Commerce Product Image Storage System

**Course:** Cloud Computing (university lab project)
**Project:** CloudCart
**Stack:** Python, Flask, SQLite, Render (free tier), Bootstrap 5, Gunicorn, pytest

---

## 1. Introduction

CloudCart is a small e-commerce application that demonstrates cloud
computing in practice. A shop owner adds products with photos. The
whole application is hosted in the cloud on **Render**, so anyone
with the link can use it — it does not depend on the owner's laptop
being switched on. Product images are stored on the server's disk
(`instance/uploads/`), while product information (name, price,
category, description) is stored in a SQLite database on the same
server. The application is a working demonstration, not a commercial
shop: there are no payments and no user accounts.

## 2. Problem Statement

When a shop only runs on one computer, three problems appear:
(1) the shop is unreachable when that computer is off; (2) the photos
are lost if that computer breaks or is replaced; (3) the shop cannot
scale or move to a hosted server. The problem is to move the
application into the cloud — host it on a cloud platform (Render) —
and to separate *product data* (small, structured, fits a database)
from *product images* (large, binary files, stored on disk and
referenced by name), and to make that separation — and the limits of
free hosting — visible and honest in the application itself.

## 3. Objectives

1. Build a working shop where products can be added, viewed, searched,
   filtered and deleted.
2. Store product images on the server's disk with unique file names.
3. Store product information in SQLite; never store image binaries in
   the database.
4. Show the real deployment status at all times — never fake it.
5. Run honestly on a local computer before it is deployed (Local Mode).
6. Deploy the application for free on Render, with the free tier's
   limits stated plainly.
7. Write tests that prove the behaviour, including the storage rules.

## 4. Methodology

The project was built in phases: (1) environment inspection
(Python 3.12.3, Git, tools); (2) project initialisation (structure,
virtual environment, pinned dependencies); (3) backend (Flask +
SQLite + disk image storage); (4) frontend (Bootstrap 5 dashboard
with sidebar); (5) deployment preparation (Render Blueprint,
`Procfile`, `runtime.txt`, documentation); (6) testing (pytest, plus
a live smoke test); (7) local demonstration; (8) final documentation
(README, Render storage guide, deployment guide, this report).
The design was later changed from Azure Blob Storage to a
Render-only design, because the owner decided to use Render and no
other cloud service — every Azure reference was removed and the
storage, templates, tests and docs were rewritten for it.

## 5. Architecture

```
User's browser
      │
      ▼
Flask application on Render (app.py)
  ├── SQLite database (instance/cloudcart.db)
  │     └── products table: id, name, price, category,
  │         description, file_name, storage_location,
  │         image_size, created_at
  └── Server disk: instance/uploads/
        └── image files, each with a unique UUID file name
```

Flow for an upload: the browser sends the image → Flask validates
type (JPG/JPEG/PNG/WebP) and size (max 5 MB) → the image is saved
on the server's disk under a unique UUID file name → only the file
name is saved in SQLite. Flow for a view: Flask reads the file name
from SQLite → the browser loads the image through the
`/uploads/<filename>` route, which only accepts UUID image names.
Flow for a delete: Flask deletes the database row and the image file
named in that row.

Running locally, the identical design runs on your own computer,
and the sidebar honestly says "Local Mode". On Render, the sidebar
says "Running on Render" — the app detects this from the `RENDER`
environment variable that Render sets itself.

## 6. Cloud Concepts

- **Cloud hosting / PaaS:** the application runs on a provider's
  servers (Render) instead of on your own computer. You push code
  to GitHub; Render builds it and serves it on a public URL.
- **Ephemeral filesystem:** on Render's free tier, files written to
  the server's disk are temporary — they can be lost on a restart
  or redeploy. This is the key limit of this design, and the app
  states it on the Cloud Storage page.
- **Object storage (the production alternative):** files stored in
  a dedicated storage service (for example Amazon S3, Azure Blob
  Storage or Cloudflare R2) instead of on the web server's disk.
  Object storage survives server restarts — the reason a real shop
  would use it. CloudCart already uses the same pattern (the
  database stores only the file's name/key); only the files' home
  would change.
- **Separation of data and files:** structured data belongs in a
  database; large binary files belong on disk or in object storage.
- **Free tier:** a limited, no-cost plan (750 hours/month, 512 MB
  RAM, sleeps after 15 idle minutes). Free is real, but it comes
  with limits — part of cloud engineering is knowing them.
- **Cold start:** the delay (about 1 minute) when a sleeping free
  service wakes up for its first visitor.

## 7. Implementation

- **Backend (`app.py`, `config.py`, `database.py`,
  `storage.py`):** Flask with an application factory,
  Flask-WTF forms with CSRF protection, SQLite access through small
  functions (`init_db`, `add_product`, `list_products`, `get_product`,
  `delete_product`, `get_stats`), and a `LocalStorage` class that
  saves images under UUID names and deletes only safely-named files.
  All settings come from environment variables; the only secret is
  `SECRET_KEY`. Deployment status is read from Render's own
  `RENDER` environment variable.
- **Frontend (`templates/`, `static/`):** Bootstrap 5 pages with a
  sidebar (Dashboard, Products, Add Product, Cloud Storage, About),
  a live deployment-status badge, statistic cards calculated from
  the real database, product cards, an Add Product form with live
  image preview, and friendly 404/500 pages.
- **Validation and security:** server-side form validation, file-type
  and size checks, safe filenames, unique file names (UUID), CSRF,
  a strict filename pattern for the image route, deletion that
  only touches the file named in the product's own row, and no stack
  traces shown to users.
- **Deployment files:** `requirements.txt` (pinned, verified),
  `Procfile` (`web: gunicorn app:app`), `render.yaml` (free Blueprint,
  only `SECRET_KEY`), `runtime.txt` (`python-3.12.3`),
  `.env.example`, `.gitignore`.

## 8. Testing

`tests/test_app.py` (pytest — no network, no cloud account needed):

| Test | Result |
|---|---|
| Dashboard loads | Pass |
| Products page loads | Pass |
| About page loads | Pass |
| Cloud Storage page explains Render + ephemeral-disk limit | Pass |
| Add rejects empty name | Pass |
| Add rejects negative price | Pass |
| Add rejects unsupported image type | Pass |
| Add rejects oversized image (> 5 MB) | Pass |
| Add succeeds: file saved with a UUID name, labelled "Render (local disk)" | Pass |
| Search by name and filter by category | Pass |
| Product detail for missing id returns 404 | Pass |
| Delete removes the row and the image file | Pass |
| Image route rejects bad filenames (`../../app.py`) | Pass |
| Storage: save creates a UUID name and the file exists | Pass |
| Storage: delete removes the file | Pass |
| Storage: delete refuses an unsafe name | Pass |

**Live smoke test:** the server was started and `/`, `/products`,
`/cloud-storage`, `/about` all returned HTTP 200;
`/products/999` returned 404; adding a product through the real form
(with a valid CSRF token) returned a redirect to `/products/1`, the
product appeared in SQLite with `storage_location='render'`, and its
image returned HTTP 200.

**Not yet verified:** the Render deployment. It needs the user's
GitHub/Render login.

## 9. Results

What works (verified): the complete shop — add, view, search,
filter, detail, delete; honest deployment-status reporting; all
validation rules; the storage rules (UUID names, safe delete,
protected image route); the full test suite; the live smoke test.
What is ready but not yet verified: the Render deployment (files
complete, waiting on the user's login). The project meets its lab
objectives except for that one live verification, which depends on
the user's accounts. Its main honest limit is the ephemeral free-tier
disk: the deployed demo is disposable, and the app says so.

## 10. Conclusion

CloudCart demonstrates the core cloud-computing idea it was built to
teach: an application does not have to live on one computer — it can
be hosted on a cloud platform, reachable from anywhere, with its data
in a database and its files on disk, each referenced by name. It also
demonstrates the honest side of cloud engineering: free hosting is
real, but it has limits (sleeping services, temporary disks), and a
good engineer states those limits instead of hiding them. The
application is complete, tested, and ready to deploy; the remaining
step is an account step (GitHub push, Render login), not a code step.

---

## 5-minute demonstration script

1. **(0:00)** Open the Dashboard. Point out the numbers are real —
   they come from the database, and the sidebar says whether the app
   is running on Render or in Local Mode. (0:30)
2. **(0:30)** Go to **Cloud Storage**. Explain that the app runs on
   Render, images live on the server's disk, and — honestly — that
   the free disk is temporary, so the demo is disposable. (1:00)
3. **(1:00)** Go to **Add Product**. Add a product with a photo.
   Explain the validation (type, size) and what happens on upload:
   unique UUID file name, only the name in SQLite. (2:00)
4. **(2:00)** Open **Products**. Search for the product by name and
   filter by category. Open its detail page and point out the file
   name, size and storage location. (3:00)
5. **(3:00)** Delete the product. Explain that the database row and
   the image file are both removed. (3:30)
6. **(3:30)** Show the tests: run `pytest -v` and point to the
   storage tests (UUID naming, safe delete, blocked file names). (4:30)
7. **(4:30)** Close: what you learned — cloud hosting vs one
   computer, separation of data and files, and why free hosting has
   limits (ephemeral disk, sleeping services). (5:00)
