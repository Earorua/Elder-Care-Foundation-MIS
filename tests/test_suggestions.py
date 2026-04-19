import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]
SUGGESTIONS_BP = ROOT / "blueprints" / "suggestions.py"
SUBMIT_TEMPLATE = ROOT / "templates" / "suggestions" / "submit.html"
ADMIN_TEMPLATE = ROOT / "templates" / "suggestions" / "admin_list.html"
BASE_TEMPLATE = ROOT / "templates" / "base.html"
I18N_JS = ROOT / "static" / "js" / "i18n.js"


def make_temp_db():
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = handle.name
    handle.close()
    conn = sqlite3.connect(db_path)
    conn.execute(
        'CREATE TABLE "User" ('
        "user_id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "user_name TEXT, password TEXT, email TEXT, is_active INTEGER, "
        "role TEXT, created_date TEXT, updated_date TEXT)"
    )
    conn.execute(
        'INSERT INTO "User" '
        "(user_name, password, email, is_active, role, created_date, updated_date) "
        "VALUES (?, ?, ?, 1, ?, date('now'), date('now'))",
        ("admin", generate_password_hash("admin123"), "admin@example.org", "admin"),
    )
    conn.execute(
        'INSERT INTO "User" '
        "(user_name, password, email, is_active, role, created_date, updated_date) "
        "VALUES (?, ?, ?, 1, ?, date('now'), date('now'))",
        ("viewer", generate_password_hash("viewer123"), "viewer@example.org", "viewer"),
    )
    conn.execute(
        'INSERT INTO "User" '
        "(user_name, password, email, is_active, role, created_date, updated_date) "
        "VALUES (?, ?, ?, 1, ?, date('now'), date('now'))",
        ("finance_user", generate_password_hash("finance123"), "finance@example.org", "finance"),
    )
    conn.execute(
        'INSERT INTO "User" '
        "(user_name, password, email, is_active, role, created_date, updated_date) "
        "VALUES (?, ?, ?, 1, ?, date('now'), date('now'))",
        (
            "coordinator",
            generate_password_hash("coord123"),
            "coordinator@example.org",
            "event_coordinator",
        ),
    )
    conn.execute("CREATE TABLE donors (donor_id INTEGER PRIMARY KEY, type TEXT)")
    conn.execute(
        "CREATE TABLE suppliers ("
        "supplier_id INTEGER PRIMARY KEY, supplier_name TEXT, contact_email TEXT)"
    )
    conn.execute(
        "CREATE TABLE gifts ("
        "gift_id INTEGER PRIMARY KEY AUTOINCREMENT, gift_name TEXT, gift_type TEXT, "
        "unit_cost REAL, description TEXT, current_stock INTEGER, min_stock_level INTEGER, "
        "is_active INTEGER, created_date TEXT)"
    )
    conn.commit()
    conn.close()
    return db_path


def make_app(db_path):
    import config
    from app import create_app

    original_database = config.DATABASE
    config.DATABASE = db_path
    try:
        app = create_app()
    finally:
        config.DATABASE = original_database
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


class SuggestionDataModelTests(unittest.TestCase):
    def test_table_helper_creates_expected_columns_and_constants(self):
        from blueprints.suggestions import (
            CATEGORIES,
            PRIORITIES,
            STATUSES,
            ensure_suggestions_table,
        )

        db_path = make_temp_db()
        try:
            conn = sqlite3.connect(db_path)
            ensure_suggestions_table(conn)
            columns = {
                row[1]: row[2]
                for row in conn.execute(
                    "PRAGMA table_info(system_optimization_suggestions)"
                ).fetchall()
            }
            conn.close()
        finally:
            os.unlink(db_path)

        self.assertEqual(
            {
                "suggestion_id": "INTEGER",
                "submitter_user_id": "INTEGER",
                "submitter_name": "TEXT",
                "submitter_role": "TEXT",
                "title": "TEXT",
                "category": "TEXT",
                "priority": "TEXT",
                "content": "TEXT",
                "status": "TEXT",
                "admin_notes": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            },
            columns,
        )
        self.assertEqual(
            (
                "Functionality",
                "Usability",
                "Performance",
                "Data Quality",
                "Security",
                "Reporting",
                "Other",
            ),
            CATEGORIES,
        )
        self.assertEqual(("Low", "Medium", "High", "Urgent"), PRIORITIES)
        self.assertEqual(("New", "Reviewed", "Planned", "Resolved"), STATUSES)


if __name__ == "__main__":
    unittest.main()
