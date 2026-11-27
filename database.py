# database.py — SQLite storage for product information.
#
# IMPORTANT: only product INFORMATION lives here (name, price,
# category, file name, size, date). Image files are NEVER stored
# in SQLite — they live on the server's disk in instance/uploads/
# (see storage.py). The database only keeps the image FILE NAME
# (a stable reference to the file on disk).
#
# The database file is created automatically on startup
# (see init_db, called from app.py).
#
# HONEST LIMIT: on Render's free tier the disk is ephemeral, so
# this database file can be lost when Render restarts or redeploys
# the service. That is explained in docs/RENDER_STORAGE.md.

import os
import sqlite3


# The columns of the "products" table. One row = one product.
#   id               - number, given automatically by SQLite
#   name             - product name, e.g. "Wireless Headphones"
#   price            - price in PKR, e.g. 4999.00
#   category         - e.g. "Electronics"
#   description      - a short text about the product
#   file_name        - the unique file name of the image on disk
#   storage_location - "render" — the image is stored on the
#                      server's local disk (Render's server when
#                      deployed, this computer when run locally)
#   image_size       - size of the image file in bytes
#   created_at       - date/time the product was added
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    file_name TEXT,
    storage_location TEXT NOT NULL DEFAULT 'render',
    image_size INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
)
"""


def get_connection(db_path):
    """Open a connection to the SQLite file, creating it if needed."""
    # Make sure the folder for the database file exists first.
    folder = os.path.dirname(db_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(db_path)
    # Rows behave like dictionaries: row["name"] works.
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    """Create the products table if it does not exist yet."""
    conn = get_connection(db_path)
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    finally:
        conn.close()


def add_product(db_path, name, price, category, description,
                file_name, storage_location, image_size, created_at):
    """Insert one new product. Returns the new product's id."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO products "
            "(name, price, category, description, file_name, "
            " storage_location, image_size, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, price, category, description, file_name,
             storage_location, image_size, created_at),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_products(db_path, search=None, category=None):
    """Return all products, newest first.

    search   - if given, only products whose name contains this text
    category - if given, only products in this category
    """
    conn = get_connection(db_path)
    try:
        sql = "SELECT * FROM products WHERE 1 = 1"
        params = []
        if search:
            # LIKE with % on both sides = "contains this text".
            sql += " AND name LIKE ?"
            params.append("%" + search + "%")
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY id DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_product(db_path, product_id):
    """Return one product by id, or None if it does not exist."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_product(db_path, product_id):
    """Delete one product row. Returns True if a row was deleted."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "DELETE FROM products WHERE id = ?", (product_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_stats(db_path):
    """Dashboard numbers, calculated from the real database.

    Returns a dictionary with:
      total_products - how many products exist
      images_stored  - how many images are stored on the server disk
      total_size     - total size of all stored images (bytes)
      average_size   - average image size (bytes, 0 if no products)
      recent         - the 5 most recently added products
    Nothing here is faked: every number comes from the database.
    """
    conn = get_connection(db_path)
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
        total_size = conn.execute(
            "SELECT COALESCE(SUM(image_size), 0) FROM products"
        ).fetchone()[0]
        recent_rows = conn.execute(
            "SELECT * FROM products ORDER BY id DESC LIMIT 5"
        ).fetchall()
        return {
            "total_products": total,
            "images_stored": total,
            "total_size": total_size,
            "average_size": total_size // total if total else 0,
            "recent": [dict(row) for row in recent_rows],
        }
    finally:
        conn.close()
