# storage.py — image storage on the server's own disk.
#
# CloudCart no longer uses Azure. Images are stored on the disk of
# the computer running the app — on your own computer when you run it
# locally, and on Render's server when the app is deployed on Render.
# That disk is the "local disk" of the server.
#
# How it works:
#   1. Save: each image gets a UNIQUE file name (a random UUID +
#      the original extension, e.g. "9f3c...a1.png") and is written
#      to instance/uploads/. The original file name is never used,
#      so two uploads can never overwrite each other and a tricky
#      file name can never escape the uploads folder.
#   2. Serve: images are shown through the /uploads/<filename>
#      route in app.py, which only accepts file names that match
#      the strict pattern below.
#   3. Delete: only a file name that matches the strict pattern
#      can be deleted, and the app only ever deletes the file named
#      in that product's own database row.
#
# HONEST LIMIT: on Render's free tier this disk is EPHEMERAL — files
# (and the SQLite database) can be lost when Render restarts or
# redeploys the service. That is stated plainly on the Cloud Storage
# page and in docs/RENDER_STORAGE.md. A production setup would use
# object storage (e.g. Amazon S3, Azure Blob Storage, Cloudflare R2)
# instead, so files survive server restarts.

import os
import re
import uuid

# A saved image file name is only valid if it looks like this:
# 32 hex characters, a dot, and jpg/jpeg/png/webp.
# This strict pattern stops anyone from asking the server for
# files outside the uploads folder (e.g. "../../app.py").
FILENAME_PATTERN = re.compile(
    r"^[0-9a-f]{32}\.(jpg|jpeg|png|webp)$"
)


class LocalStorage:
    """Saves, deletes and finds product images on the server's disk."""

    def __init__(self, folder):
        """folder is where images live, e.g. instance/uploads/."""
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def save(self, data, original_filename):
        """Save image bytes under a new unique name.

        Returns the unique file name that was created.
        The original file name is only used for its extension.
        """
        ext = os.path.splitext(original_filename)[1].lower()
        filename = uuid.uuid4().hex + ext
        path = os.path.join(self.folder, filename)
        with open(path, "wb") as out:
            out.write(data)
        return filename

    def delete(self, filename):
        """Delete one image file — but ONLY if the name is safe.

        Returns True if a file was deleted, False otherwise.
        A name that does not match the strict pattern is never
        touched, so a bad value in the database can never delete
        an arbitrary file.
        """
        if not filename or not FILENAME_PATTERN.match(filename):
            return False
        path = os.path.join(self.folder, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, filename):
        """True if a safely-named image file exists on disk."""
        if not filename or not FILENAME_PATTERN.match(filename):
            return False
        return os.path.exists(os.path.join(self.folder, filename))
