# app.py — CloudCart: the Flask application.
#
# What this file does:
#   * Creates the Flask app (exposed as "app" at module level,
#     so Gunicorn can run it with "gunicorn app:app").
#   * Reads all settings from environment variables (config.py).
#   * Creates the SQLite database automatically on startup.
#   * Stores product images on the server's own disk
#     (instance/uploads/) through storage.py — there is no
#     separate cloud storage service any more. The "cloud" in
#     this project is Render: the app itself runs on Render's
#     servers instead of on one local computer.
#   * Serves the pages: Dashboard, Products, Add Product,
#     Product Detail, Cloud Storage, About.
#
# HONEST LIMIT: on Render's free tier the server's disk is
# ephemeral, so images and the SQLite database can be lost when
# Render restarts or redeploys the service. The Cloud Storage
# page says this plainly — the app never pretends otherwise.
#
# How to run it locally:
#   python -m venv venv
#   venv/Scripts/activate        (Windows PowerShell)
#   source venv/bin/activate     (Mac / Linux)
#   pip install -r requirements.txt
#   python app.py
#   Then open http://127.0.0.1:5000

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory, abort,
)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, DecimalField, SelectField, TextAreaField, FileField
from wtforms.validators import DataRequired, NumberRange

from config import Config, is_render_hosted
from database import (
    init_db, add_product, list_products, get_product,
    delete_product, get_stats,
)
from storage import LocalStorage, FILENAME_PATTERN

# Load variables from a local ".env" file if it exists.
# On Render there is no .env file; variables come from the dashboard.
load_dotenv()

# How big an uploaded image may be: 5 MB (from the spec).
MAX_FILE_SIZE = 5 * 1024 * 1024


def allowed_file(filename):
    """True if the filename has an allowed image extension."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


# ----------------------------------------------------------------
#  The Add Product form (Flask-WTF gives us CSRF protection
#  and server-side validation for free).
# ----------------------------------------------------------------
class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired()])
    price = DecimalField(
        "Price (PKR)",
        validators=[DataRequired(), NumberRange(min=0,
                                               message="Price cannot be negative.")],
    )
    category = SelectField(
        "Category", choices=[(c, c) for c in Config.CATEGORIES]
    )
    description = TextAreaField("Description")
    image = FileField("Product image")


def create_app(config_overrides=None):
    """Build the Flask app. Tests pass overrides (test database,
    CSRF off) so they never touch the real database."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    # Tests pass INSTANCE_PATH to keep their database and uploads
    # in a temporary folder, away from the real instance folder.
    if config_overrides and "INSTANCE_PATH" in config_overrides:
        app.instance_path = config_overrides["INSTANCE_PATH"]

    # CSRF protection for all forms (spec section 10).
    CSRFProtect(app)

    # Where the SQLite database lives.
    db_path = app.config.get("DATABASE_PATH") or os.path.join(
        app.instance_path, Config.DATABASE
    )
    app.config["DATABASE_PATH"] = db_path
    init_db(db_path)

    # Where product images live: instance/uploads/
    # (on the server's disk — Render's server when deployed).
    uploads = os.path.join(app.instance_path, "uploads")
    app.config["UPLOADS"] = uploads
    app.storage = LocalStorage(uploads)

    # Is this app really running on Render? Render sets
    # RENDER=true itself; locally it is not set, so the app
    # honestly says "Local Mode" instead.
    app.render_hosted = is_render_hosted()

    # ------------------------------------------------------------
    #  Helper: where does a product's image come from?
    # ------------------------------------------------------------
    def image_url_for(product):
        """Return a URL for a product's image.

        Every image is served by the /uploads/<filename> route,
        which only accepts strictly-valid file names.
        """
        return url_for("uploaded_file", filename=product["file_name"])

    app.jinja_env.globals["image_url_for"] = image_url_for

    # Make the deployment status available in every template
    # (sidebar badge: "Running on Render" or "Local Mode").
    @app.context_processor
    def inject_status():
        return {"render_hosted": app.render_hosted}

    # ------------------------------------------------------------
    #  ROUTES
    # ------------------------------------------------------------

    @app.route("/")
    def dashboard():
        """Home page: real statistics, calculated from the database."""
        stats = get_stats(db_path)
        return render_template("dashboard.html", stats=stats)

    @app.route("/products")
    def products():
        """Product list, with search by name and filter by category."""
        search = request.args.get("q", "").strip() or None
        category = request.args.get("category", "").strip() or None
        items = list_products(db_path, search=search, category=category)
        return render_template(
            "products.html", products=items,
            categories=Config.CATEGORIES,
            search=search or "", category=category or "",
        )

    @app.route("/products/<int:product_id>")
    def product_detail(product_id):
        """One product, large, with all its details."""
        product = get_product(db_path, product_id)
        if product is None:
            abort(404)
        return render_template("product_detail.html", product=product)

    @app.route("/add", methods=["GET", "POST"])
    def add_product_page():
        """Add a product: form, image upload, validation."""
        form = ProductForm()
        if form.validate_on_submit():
            # --- Validate the image file ---
            file = request.files.get("image")
            if file is None or file.filename == "":
                flash("Please choose an image file.", "danger")
                return render_template("add_product.html", form=form)
            if not allowed_file(file.filename):
                flash("Only JPG, JPEG, PNG and WebP images are allowed.",
                      "danger")
                return render_template("add_product.html", form=form)

            # Read the file once, so we can check its real size.
            data = file.read()
            if len(data) > MAX_FILE_SIZE:
                flash("Image is too large. Maximum size is 5 MB.", "danger")
                return render_template("add_product.html", form=form)
            if len(data) == 0:
                flash("The image file is empty.", "danger")
                return render_template("add_product.html", form=form)

            # --- Store the image on the server's disk ---
            # A unique UUID file name is created, so two uploads
            # can never overwrite each other.
            file_name = app.storage.save(data, file.filename)

            # --- Save the product information in SQLite ---
            # Only the file NAME is saved — never the image itself.
            product_id = add_product(
                db_path,
                name=form.name.data.strip(),
                price=float(form.price.data),
                category=form.category.data,
                description=(form.description.data or "").strip(),
                file_name=file_name,
                storage_location="render",
                image_size=len(data),
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            where = "on Render" if app.render_hosted \
                else "on this computer (Local Mode)"
            flash(f"Product added! Image stored {where}.", "success")
            return redirect(url_for("product_detail", product_id=product_id))

        # If the form had errors (empty name, negative price...),
        # Flask-WTF shows them next to the fields.
        return render_template("add_product.html", form=form)

    @app.route("/products/<int:product_id>/delete", methods=["POST"])
    def delete_product_page(product_id):
        """Delete a product AND its image.

        Only the file named in this product's own database row is
        deleted, and only after the name passes the strict pattern
        check inside storage.delete().
        """
        product = get_product(db_path, product_id)
        if product is None:
            abort(404)

        app.storage.delete(product["file_name"])
        delete_product(db_path, product_id)
        flash(f"Deleted: {product['name']}", "success")
        return redirect(url_for("products"))

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        """Serve a stored product image.

        The filename must match the strict pattern exactly,
        otherwise this returns 404. Nothing outside the uploads
        folder can be reached through this route.
        """
        if not FILENAME_PATTERN.match(filename):
            abort(404)
        return send_from_directory(uploads, filename)

    @app.route("/cloud-storage")
    def cloud_storage():
        """Cloud Storage page: how storage really works here.

        The app runs on Render (the cloud platform) and images are
        stored on the server's disk. The page also states the
        honest free-tier limit: that disk is ephemeral, so images
        and the database can be lost on a restart or redeploy.
        """
        stats = get_stats(db_path)
        return render_template(
            "cloud_storage.html",
            stats=stats,
            render_hosted=app.render_hosted,
        )

    @app.route("/about")
    def about():
        """About the project: what it is and how it works."""
        return render_template("about.html")

    # ------------------------------------------------------------
    #  Error pages (no raw stack traces are shown to the user)
    # ------------------------------------------------------------
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("500.html"), 500

    @app.errorhandler(413)
    def file_too_large(error):
        flash("Image is too large. Maximum size is 5 MB.", "danger")
        return redirect(url_for("add_product_page"))

    return app


# The app object at module level, so Gunicorn can run it:
#   gunicorn app:app
app = create_app()


if __name__ == "__main__":
    # Local development server. Debug is off by default so that
    # errors show the friendly 500 page instead of a stack trace.
    app.run(debug=False)
