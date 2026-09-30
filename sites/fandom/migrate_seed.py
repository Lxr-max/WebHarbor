"""Reconcile frozen revision and file metadata with the shipped source bytes."""
from pathlib import Path
import sqlite3
import json
from PIL import Image


def migrate(path=None):
    root = Path(__file__).resolve().parent
    path = Path(path) if path else root / "instance_seed" / "fandom.db"
    with sqlite3.connect(path) as connection:
        # Corrected from the Genshin data archive, accessed 2026-09-29:
        # https://genshin-db-api.vercel.app/api/v5/characters?query=zhongli
        row = connection.execute("SELECT id, infobox_json FROM articles WHERE slug='Zhongli' AND wiki_id=3").fetchone()
        if row:
            info = json.loads(row[1])
            if info.get('constellation') != 'Lapis Dei':
                info['constellation'] = 'Lapis Dei'
                connection.execute("UPDATE articles SET infobox_json=? WHERE id=?", (json.dumps(info), row[0]))
        previous = {}
        rows = connection.execute("SELECT id, article_id, content, bytes_size, bytes_delta FROM revisions ORDER BY article_id, timestamp, id").fetchall()
        for identifier, article, content, stored_size, stored_delta in rows:
            size = len((content or "").encode("utf-8"))
            delta = size - previous.get(article, 0)
            if (stored_size, stored_delta) != (size, delta):
                connection.execute("UPDATE revisions SET bytes_size=?, bytes_delta=? WHERE id=?", (size, delta, identifier))
            previous[article] = size
        for identifier, filename, width, height, size in connection.execute("SELECT id, filename, width, height, bytes_size FROM files").fetchall():
            image_path = path.resolve().parent.parent / "static" / "images" / filename
            if not image_path.is_file():
                raise RuntimeError(f"Missing file asset: {filename}")
            with Image.open(image_path) as image:
                image.load()
                actual = (*image.size, image_path.stat().st_size)
            if (width, height, size) != actual:
                connection.execute("UPDATE files SET width=?, height=?, bytes_size=? WHERE id=?", (*actual, identifier))

if __name__ == "__main__":
    import sys
    migrate(sys.argv[1] if len(sys.argv) > 1 else None)
