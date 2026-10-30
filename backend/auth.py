"""User accounts and login (salted PBKDF2 password hashes, no plaintext storage)."""
import hashlib
import hmac
import os
import sqlite3

from backend.database import get_connection, init_db, query

ITERATIONS = 200_000


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)


def create_user(username, password, role="staff"):
    if role not in ("admin", "staff"):
        raise ValueError("role must be 'admin' or 'staff'")
    init_db()
    salt = os.urandom(16)
    stored = salt.hex() + ":" + _hash(password, salt).hex()
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username.strip(), stored, role))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"User '{username}' already exists")


def authenticate(username, password):
    """Return {'id', 'username', 'role'} on success, None on failure."""
    rows = query("SELECT * FROM users WHERE username = ?", (username.strip(),))
    if not rows:
        return None
    salt_hex, hash_hex = rows[0]["password_hash"].split(":")
    candidate = _hash(password, bytes.fromhex(salt_hex)).hex()
    if hmac.compare_digest(candidate, hash_hex):
        u = rows[0]
        return {"id": u["id"], "username": u["username"], "role": u["role"]}
    return None


def ensure_default_admin():
    """Create admin/admin123 on first run so the app is usable immediately."""
    init_db()
    if not query("SELECT 1 FROM users LIMIT 1"):
        create_user("admin", "admin123", "admin")
