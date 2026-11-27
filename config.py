# config.py — all settings for CloudCart live here.
#
# Every secret comes from ENVIRONMENT VARIABLES, never from code.
# Locally, those variables live in a ".env" file (see .env.example).
# On Render, they are set in the Render dashboard.
#
# There is no cloud-storage account to configure any more:
# images are stored on the server's own disk (see storage.py).
# The only secret is SECRET_KEY.

import os


class Config:
    """One small class holding every setting the app needs."""

    # SECRET_KEY signs the session cookie and the CSRF token.
    # Change it in .env / on Render. Never commit the real value.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # The SQLite database file. Flask puts it in instance/cloudcart.db.
    DATABASE = os.environ.get("DATABASE_PATH", "cloudcart.db")

    # --- Upload rules (from the project spec, section 10) ---
    # Only these image types are accepted.
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

    # Maximum file size: 5 MB. Flask refuses bigger uploads.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB in bytes

    # Product categories shown in the Add Product form.
    CATEGORIES = [
        "Electronics",
        "Clothing",
        "Home & Kitchen",
        "Books",
        "Sports",
        "Other",
    ]


def is_render_hosted():
    """True when the app is really running on Render.

    Render automatically sets the environment variable
    RENDER=true on every service it runs. Locally it is not set,
    so this is False and the app honestly says "Local Mode".
    Nothing here is guessed or faked — it is read from the
    environment Render itself provides.
    """
    return os.environ.get("RENDER") == "true"
