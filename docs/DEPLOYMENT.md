# Deployment Guide — CloudCart on Render (free tier)

## Why Render?

Render was chosen because its free tier fits this lab project: no
credit card required, a simple GitHub-to-live-site flow, and a
`render.yaml` Blueprint so the service can be recreated in one click.
Render is the whole cloud platform for this project — it hosts the
app, and the app stores images on the server's disk. There is no
other cloud service to configure.

**Render free-tier terms** (as stated in the project brief, November
2026 — **re-check Render's own pricing page at deployment time**,
because free tiers change): 750 instance-hours per workspace per
month, 512 MB RAM, no credit card required, services spin down after
15 minutes without traffic with about a 1-minute cold start, and an
ephemeral filesystem with no persistent disk on the free tier.

### Why not the alternatives?

(Also from the November 2026 research in the brief — re-verify before
repeating these as fact.)

- **Railway:** free plan was only a $1/month usage credit plus a
  one-time $5/30-day trial — too small for an always-on demo.
- **PythonAnywhere:** the free Beginner plan is easy for beginners,
  but free accounts have restricted outbound internet.
- **Heroku:** has had no free tier since November 2022.

## Free-tier consequences (read before deploying)

- The service **sleeps after 15 minutes idle**; the first visit after
  that takes about a minute (cold start). This is normal.
- The filesystem is **ephemeral**: the SQLite database file AND the
  uploaded images can be lost on a restart or redeploy. The deployed
  demo is **disposable** — re-add products after a restart. This is
  the biggest limit of the Render-only design; see
  `docs/RENDER_STORAGE.md` for what a production setup would use
  instead (object storage).
- If the 750 free hours are exhausted, free services are suspended
  until the next month. **Do not use uptime-pinging / self-pinging**
  to prevent sleeping.
- Render free needs no card, so it cannot charge you unless you
  upgrade. **Never upgrade to a paid instance type, add a card, or
  enable a paid add-on without a deliberate decision.**

## Prerequisites

1. This project, verified locally (`python app.py` works, `pytest`
   passes).
2. A GitHub account (the user already has one: `NoumanArshad0321`).
3. A Render account (free, sign up with GitHub).
4. A `SECRET_KEY` — you generate it yourself and paste it into the
   Render dashboard, never into chat.

## Step 1 — Push the project to GitHub

Create a new repository named **CloudCart** on GitHub (do not initialise
it with a README — the project already has one), then, from the
project folder:

```powershell
git init
git add .
git status
```

**Check `git status` carefully:** `.env` and any `.db` file must NOT
appear in the list. They are in `.gitignore`. If they do appear, stop
and fix `.gitignore` before continuing.

```powershell
git commit -m "Add CloudCart"
git branch -M main
git remote add origin https://github.com/NoumanArshad0321/CloudCart.git
git push -u origin main
```

## Step 2 — Create the Render service

Option A — Blueprint (recommended, uses `render.yaml` in this repo):

1. In Render, click **New → Blueprint**.
2. Connect/select the `CloudCart` GitHub repository.
3. Render reads `render.yaml` and proposes a web service named
   `cloudcart`, Free plan, build `pip install -r requirements.txt`,
   start `gunicorn app:app`.
4. Apply it.

Option B — Manual Web Service:

1. In Render, click **New → Web Service**, select the `CloudCart` repo.
2. Name: `cloudcart`. Runtime: **Python**. Region: nearest to you.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Instance Type: **Free**.

## Step 3 — Set the environment variable in Render

In the service's **Environment** tab, add this (never in git):

| Key | Value |
|---|---|
| `SECRET_KEY` | Generate a long random string (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`) |

That is the only secret this project has. `render.yaml` marks it as
`sync: false`, which means Render asks for it in the dashboard
instead of reading it from the file.

## Step 4 — Deploy and get the public URL

1. Click **Deploy** (or it deploys automatically after the first push).
2. Wait for the build to finish — watch the deploy logs for errors.
3. Copy the public URL, e.g. `https://cloudcart-xxxx.onrender.com`.

## Step 5 — Verify the public URL

Do each of these on the **live** URL, not locally:

1. **Dashboard loads** (HTTP 200) and shows real numbers.
2. **Deployment status is accurate** — the sidebar says
   "Running on Render" and the Cloud Storage page explains the
   storage design and its ephemeral-disk limit.
3. **Add Product works** — add a product with a real image; it
   should say the image was stored on Render.
4. **Search and filtering work** on the Products page.
5. **The image displays** from the deployed app.
6. **Deletion works** — delete the product and confirm its image
   is gone too (the product disappears from the list).

## Step 6 — Report honestly

Write down the public URL and exactly which of the steps above passed.
**Do not claim the deployment succeeded if any step failed.** If a
step fails, note the error from the Render deploy logs and fix that
step before claiming success.

## Current status (26 Nov 2026)

- Local verification: **done** (pytest tests passed; live smoke test
  passed — see README).
- GitHub push: **not yet done** — the user pushes the repo himself.
- Render deployment: **not yet attempted** — it needs the user's
  GitHub/Render login.

## Billing safety checklist

- [ ] Free instance type selected (not Starter or above).
- [ ] No card added to Render.
- [ ] No paid add-on enabled.
- [ ] No uptime-pinging service set up.
