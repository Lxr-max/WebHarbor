"""Build source JSON into SQLite; runtime handlers never read source JSON."""
import hashlib
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SEED_VERSION = "doj-2026-09-27-v1"
BENCHMARK_USERS = [
    ("alice_j", "alice.j@test.com", "Alice Johnson"),
    ("bob_c", "bob.c@test.com", "Bob Chen"),
    ("carol_d", "carol.d@test.com", "Carol Davis"),
    ("david_k", "david.k@test.com", "David Kim"),
]
# Fixed public benchmark password hash, never a credential for the real DOJ.
TEST_PASSWORD_HASH = "pbkdf2:sha256:600000$webharbordojseed$" + hashlib.pbkdf2_hmac(
    "sha256", b"TestPass123!", b"webharbordojseed", 600000
).hex()


def seed_database(db, Page, SnapshotMeta):
    if db.session.scalar(db.select(Page.id).limit(1)) is not None:
        return
    data_path = BASE_DIR / "source_data.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    records = data["pages"]
    paths = [p["path"] for p in records]
    if not records or len(paths) != len(set(paths)):
        raise ValueError("The source snapshot must contain unique, non-empty page records")
    for record in sorted(records, key=lambda p: p["path"]):
        db.session.add(Page(**record))
    db.session.add(SnapshotMeta(key="seed_version", value=SEED_VERSION))
    db.session.add(SnapshotMeta(key="source_file_sha256", value=hashlib.sha256(data_path.read_bytes()).hexdigest()))
    db.session.add(SnapshotMeta(key="snapshot", value=data["snapshot"]))
    asset_routes = data.get('asset_routes', {})
    if any(not record['path'].startswith('static/external_cache/') or '..' in Path(record['path']).parts
           for record in asset_routes.values()):
        raise ValueError('Document aliases must refer to local external-cache assets')
    db.session.add(SnapshotMeta(key="asset_routes", value=asset_routes))
    db.session.commit()


def seed_benchmark_users(db, User):
    if db.session.scalar(db.select(User.id).where(User.email == "alice.j@test.com")) is not None:
        return
    for username, email, display_name in BENCHMARK_USERS:
        db.session.add(User(username=username, email=email, display_name=display_name, password_hash=TEST_PASSWORD_HASH))
    db.session.commit()


def freeze_seed():
    from app import app, db
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
    output = BASE_DIR / "instance_seed"
    output.mkdir(exist_ok=True)
    shutil.copy2(Path(app.instance_path) / "us_doj.db", output / "us_doj.db")
    print(f"Frozen DOJ seed: {output / 'us_doj.db'}")


if __name__ == "__main__":
    freeze_seed()
