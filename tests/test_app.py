# tests/test_app.py — pytest tests for CloudCart (Render-only design).
#
# How to run them:  pytest -v
#
# What is tested here:
#   * Pages load (Dashboard, Products, Cloud Storage, About).
#   * The Cloud Storage page explains Render and the ephemeral-disk
#     limit honestly.
#   * Product validation: empty name, negative price, bad image type,
#     oversized image.
#   * Full CRUD: add a product, list it, search/filter, view details,
#     delete it (row AND image file are removed).
#   * Local storage rules: uploading saves a file with a UUID name,
#     deleting removes the file, unsafe names are refused, and the
#     image route rejects ../../-style file names.
#
# No network and no cloud account are needed for any test here.

import io
import os
import re
import sys

import pytest

# Make "app", "database" and "storage" importable from tests/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from storage import LocalStorage, FILENAME_PATTERN  # noqa: E402

# A tiny valid 1x1 PNG, as bytes (so tests can upload a real image
# file without needing any file on disk).
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f"
    b"\x00\x00\x01\x01\x00\x05\xe2\x9c\x8f\x00\x00\x00\x00IEND\xaeB`\x82"
)

# A UUID file name looks like 32 hex characters + an extension.
UUID_FILENAME = re.compile(r"^[0-9a-f]{32}\.png$")


@pytest.fixture
def client(tmp_path):
    """A test client with its own empty database and uploads folder."""
    instance = tmp_path / "instance"
    instance.mkdir()
    test_app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,  # tests post forms without a token
        "DATABASE_PATH": str(tmp_path / "test.db"),
        "INSTANCE_PATH": str(instance),
        "SECRET_KEY": "test-secret",
    })
    with test_app.test_client() as test_client:
        yield test_client


def add_test_product(client, name="Wireless Headphones", price="4999",
                     category="Electronics"):
    """Helper: add one product through the real Add Product form."""
    data = {
        "name": name,
        "price": price,
        "category": category,
        "description": "Test product",
        "image": (io.BytesIO(PNG_BYTES), "photo.png"),
    }
    return client.post("/add", data=data,
                       content_type="multipart/form-data",
                       follow_redirects=True)


# ----------------------------------------------------------------
#  1. Pages load
# ----------------------------------------------------------------
def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Total products" in response.data


def test_products_page_loads(client):
    assert client.get("/products").status_code == 200


def test_about_page_loads(client):
    assert client.get("/about").status_code == 200


def test_cloud_storage_page_explains_render_and_limits(client):
    """The page must name Render and state the ephemeral-disk limit."""
    response = client.get("/cloud-storage")
    assert response.status_code == 200
    assert b"Render" in response.data
    assert b"ephemeral" in response.data
    assert b"Local Mode" in response.data


# ----------------------------------------------------------------
#  2. Validation
# ----------------------------------------------------------------
def test_add_product_rejects_empty_name(client):
    response = add_test_product(client, name="")
    assert b"This field is required" in response.data
    # Nothing was saved.
    assert b"Wireless Headphones" not in client.get("/products").data


def test_add_product_rejects_negative_price(client):
    response = add_test_product(client, price="-100")
    assert b"Price cannot be negative" in response.data
    assert b"Wireless Headphones" not in client.get("/products").data


def test_add_product_rejects_unsupported_image(client):
    data = {
        "name": "Bad File",
        "price": "100",
        "category": "Books",
        "description": "",
        "image": (io.BytesIO(b"not an image"), "notes.txt"),
    }
    response = client.post("/add", data=data,
                           content_type="multipart/form-data",
                           follow_redirects=True)
    assert b"Only JPG, JPEG, PNG and WebP" in response.data
    assert b"Bad File" not in client.get("/products").data


def test_add_product_rejects_oversized_image(client):
    big = b"x" * (5 * 1024 * 1024 + 1)  # just over 5 MB
    data = {
        "name": "Huge Image",
        "price": "100",
        "category": "Books",
        "description": "",
        "image": (io.BytesIO(big), "huge.png"),
    }
    response = client.post("/add", data=data,
                           content_type="multipart/form-data",
                           follow_redirects=False)
    # Flask refuses the oversized upload (413) and our handler
    # sends the user back to the Add page.
    assert response.status_code in (302, 413)


# ----------------------------------------------------------------
#  3. Full CRUD on Render (local disk) storage
# ----------------------------------------------------------------
def test_add_product_success_saves_uuid_file(client, tmp_path):
    response = add_test_product(client)
    assert response.status_code == 200
    assert b"Wireless Headphones" in response.data
    # The detail page says honestly where the image lives.
    assert b"Render (local disk)" in response.data
    # The image file really exists, under a UUID file name.
    uploads = list((tmp_path / "instance" / "uploads").glob("*.png"))
    assert len(uploads) == 1
    assert UUID_FILENAME.match(uploads[0].name)


def test_search_and_filter(client):
    add_test_product(client, name="Wireless Headphones", category="Electronics")
    add_test_product(client, name="Cotton T-Shirt", category="Clothing")

    # Search by name: only the headphones match "head".
    page = client.get("/products?q=head")
    assert b"Wireless Headphones" in page.data
    assert b"Cotton T-Shirt" not in page.data

    # Filter by category: only the shirt matches "Clothing".
    page = client.get("/products?category=Clothing")
    assert b"Cotton T-Shirt" in page.data
    assert b"Wireless Headphones" not in page.data


def test_product_detail_404(client):
    assert client.get("/products/999").status_code == 404


def test_delete_removes_row_and_image_file(client, tmp_path):
    add_test_product(client)
    uploads = list((tmp_path / "instance" / "uploads").glob("*.png"))
    assert len(uploads) == 1

    response = client.post("/products/1/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Deleted: Wireless Headphones" in response.data
    # The database row is gone...
    assert b"Wireless Headphones" not in client.get("/products").data
    # ...and the image file is gone too.
    assert not uploads[0].exists()


def test_uploads_route_rejects_bad_filename(client):
    # A path trick like ../../app.py must never work here.
    assert client.get("/uploads/../../app.py").status_code == 404
    assert client.get("/uploads/not-a-real-file.txt").status_code == 404


# ----------------------------------------------------------------
#  4. Storage unit tests (storage.py, no HTTP involved)
# ----------------------------------------------------------------
def test_storage_save_creates_uuid_name(tmp_path):
    storage = LocalStorage(str(tmp_path))
    name = storage.save(b"fake image", "My Photo.JPG")
    # UUID name, original extension kept (lowercased).
    assert FILENAME_PATTERN.match(name)
    assert name.endswith(".jpg")
    assert storage.exists(name)


def test_storage_delete_removes_file(tmp_path):
    storage = LocalStorage(str(tmp_path))
    name = storage.save(b"fake image", "photo.png")
    assert storage.delete(name) is True
    assert not storage.exists(name)


def test_storage_delete_refuses_unsafe_name(tmp_path):
    storage = LocalStorage(str(tmp_path))
    # None of these may ever delete anything.
    assert storage.delete("../../app.py") is False
    assert storage.delete("/etc/passwd") is False
    assert storage.delete("") is False
    assert storage.delete(None) is False
