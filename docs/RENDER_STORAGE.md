# How Storage Works on Render — CloudCart

## The short version

CloudCart stores product images **on the disk of the server that
runs the app** — in the folder `instance/uploads/`. Product
information (name, price, category, the image's file name, size,
date) is stored in a SQLite database file on the same disk
(`instance/cloudcart.db`). There is no separate cloud storage
service: the "cloud" in this project is **Render itself**, the
platform that hosts the app.

## The flow, step by step

1. You upload an image on the Add Product page.
2. Flask checks the file type (JPG, JPEG, PNG, WebP) and size
   (max 5 MB). Anything else is rejected.
3. The image is saved under a **unique file name**: a random UUID
   plus the original extension, e.g.
   `9f3c2a1b4d5e6f708192a3b4c5d6e7f8.png`. The original file name
   is never used, so two uploads can never overwrite each other.
4. Only the file name is saved in SQLite — never the image itself.
   Storing binary files in a database would make it slow and huge.
5. When an image is displayed, the browser asks for
   `/uploads/<filename>`. That route only accepts file names that
   match the strict pattern `32 hex characters + .jpg/.jpeg/.png/
   .webp`, so nobody can use it to read other files on the server
   (for example `../../app.py` is rejected with 404).
6. Deleting a product deletes its database row **and** its image
   file, so nothing is left behind.

## The honest limit: Render's free disk is ephemeral

On Render's free tier, the service's filesystem is **ephemeral**
(temporary). That means:

- Files you upload — and the SQLite database itself — can be
  **lost when Render restarts the service or when you redeploy**.
- The deployed demo is therefore **disposable**: after a restart
  you re-add the products.
- The free service also **sleeps after 15 minutes without
  visitors**; the first visit after that takes about a minute
  (cold start). This is normal and costs nothing.

This limit is stated plainly on the Cloud Storage page of the app
itself, not hidden in a footnote — a lab demo should never pretend
its storage is permanent when it is not.

## Why this design is still a good lab project

- It demonstrates the real cloud idea: your app no longer depends
  on your own laptop. It runs on a provider's servers and is
  reachable from anywhere, from a GitHub push.
- It shows the separation of concerns: structured data in a
  database, binary files on disk, each referenced by name.
- It teaches the trade-off honestly: free hosting is real, but
  "free" comes with limits (sleeping, temporary disk), and part of
  cloud engineering is choosing the right storage for the job.

## What a production setup would use instead

**Object storage** — for example Amazon S3, Azure Blob Storage,
or Cloudflare R2. In object storage:

- Files live **outside** the web server, in the provider's storage
  service, so they survive restarts, redeploys and even the
  replacement of the whole server.
- Files are addressed by a unique key (like our UUID file name) in
  a container/bucket, and are served directly by the storage
  service, which scales to any number of users.
- The database still only stores the file's key — exactly the same
  pattern CloudCart already uses, just with a durable home for the
  files.

For a production shop you would also replace SQLite with a hosted
database (for example Render's free PostgreSQL), for the same
reason: so the product data survives restarts too.

## Cost

- Render free tier: no credit card, no charge unless you upgrade.
  Never upgrade to a paid plan, add a card, or enable a paid add-on
  without a deliberate decision.
- Object storage (if you ever add it): providers charge a small
  amount per GB stored and per request — check current pricing
  first, and never assume it is completely free.
