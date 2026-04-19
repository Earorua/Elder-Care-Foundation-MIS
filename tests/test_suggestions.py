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

    def test_app_startup_creates_suggestions_table(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            with app.app_context():
                conn = sqlite3.connect(db_path)
                columns = [
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(system_optimization_suggestions)"
                    ).fetchall()
                ]
                conn.close()
        finally:
            os.unlink(db_path)

        self.assertIn("suggestion_id", columns)
        self.assertIn("submitter_user_id", columns)

    def test_anonymous_user_is_redirected_from_submission_page_to_login(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            response = app.test_client().get("/suggestions")
        finally:
            os.unlink(db_path)

        self.assertEqual(302, response.status_code)
        self.assertIn("/login", response.headers["Location"])
        self.assertIn("next=", response.headers["Location"])

    def test_any_authenticated_role_can_load_submission_page(self):
        for username, password in [
            ("viewer", "viewer123"),
            ("finance_user", "finance123"),
            ("coordinator", "coord123"),
            ("admin", "admin123"),
        ]:
            with self.subTest(username=username):
                db_path = make_temp_db()
                try:
                    app = make_app(db_path)
                    client = app.test_client()
                    login_response = login(client, username, password)
                    response = client.get("/suggestions")
                finally:
                    os.unlink(db_path)

                self.assertEqual(302, login_response.status_code)
                self.assertEqual(200, response.status_code)
                self.assertIn(b"System Optimization Suggestions", response.data)

    def test_authenticated_user_can_submit_suggestion_with_account_snapshot(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            response = client.post(
                "/suggestions",
                data={
                    "title": "Improve dashboard filters",
                    "category": "Usability",
                    "priority": "High",
                    "content": "Please add saved filter presets to the dashboard.",
                },
                follow_redirects=False,
            )
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM system_optimization_suggestions"
            ).fetchone()
            conn.close()
        finally:
            os.unlink(db_path)

        self.assertEqual(302, response.status_code)
        self.assertEqual("Improve dashboard filters", row["title"])
        self.assertEqual("Usability", row["category"])
        self.assertEqual("High", row["priority"])
        self.assertEqual(
            "Please add saved filter presets to the dashboard.", row["content"]
        )
        self.assertEqual("New", row["status"])
        self.assertEqual("viewer", row["submitter_name"])
        self.assertEqual("viewer", row["submitter_role"])
        self.assertIsNotNone(row["created_at"])
        self.assertIsNotNone(row["updated_at"])

    def test_submission_rejects_empty_text_and_invalid_fixed_values(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            response = client.post(
                "/suggestions",
                data={
                    "title": "   ",
                    "category": "Bad Category",
                    "priority": "Bad Priority",
                    "content": "",
                },
                follow_redirects=True,
            )
            conn = sqlite3.connect(db_path)
            count = conn.execute(
                "SELECT COUNT(*) FROM system_optimization_suggestions"
            ).fetchone()[0]
            conn.close()
        finally:
            os.unlink(db_path)

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, count)
        self.assertIn(b"Please enter a suggestion title", response.data)
        self.assertIn(b"Please enter suggestion details", response.data)
        self.assertIn(b"Please select a valid suggestion category", response.data)
        self.assertIn(b"Please select a valid suggestion priority", response.data)

    def test_non_admin_cannot_access_admin_suggestions(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            response = client.get("/admin/suggestions", follow_redirects=False)
        finally:
            os.unlink(db_path)

        self.assertEqual(302, response.status_code)
        self.assertIn("/", response.headers["Location"])

    def test_admin_can_see_submitted_suggestions(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            client.post(
                "/suggestions",
                data={
                    "title": "Add printable schedule",
                    "category": "Reporting",
                    "priority": "Medium",
                    "content": "A print-friendly schedule view would help coordinators.",
                },
            )
            client.get("/logout")
            login(client, "admin", "admin123")
            response = client.get("/admin/suggestions")
        finally:
            os.unlink(db_path)

        self.assertEqual(200, response.status_code)
        self.assertIn(b"Add printable schedule", response.data)
        self.assertIn(b"viewer", response.data)
        self.assertIn(b"Reporting", response.data)

    def test_admin_can_update_suggestion_status_and_notes(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            client.post(
                "/suggestions",
                data={
                    "title": "Speed up BI charts",
                    "category": "Performance",
                    "priority": "Urgent",
                    "content": "Large chart queries should return faster.",
                },
            )
            client.get("/logout")
            login(client, "admin", "admin123")
            response = client.post(
                "/admin/suggestions/1/status",
                data={"status": "Planned", "admin_notes": "Queued for the next release."},
                follow_redirects=False,
            )
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT status, admin_notes FROM system_optimization_suggestions "
                "WHERE suggestion_id = 1"
            ).fetchone()
            conn.close()
        finally:
            os.unlink(db_path)

        self.assertEqual(302, response.status_code)
        self.assertEqual("Planned", row["status"])
        self.assertEqual("Queued for the next release.", row["admin_notes"])

    def test_admin_status_update_rejects_invalid_status(self):
        db_path = make_temp_db()
        try:
            app = make_app(db_path)
            client = app.test_client()
            login(client, "viewer", "viewer123")
            client.post(
                "/suggestions",
                data={
                    "title": "Improve search",
                    "category": "Functionality",
                    "priority": "Low",
                    "content": "Search should include notes.",
                },
            )
            client.get("/logout")
            login(client, "admin", "admin123")
            response = client.post(
                "/admin/suggestions/1/status",
                data={"status": "Bad Status", "admin_notes": "No change"},
                follow_redirects=True,
            )
            conn = sqlite3.connect(db_path)
            status = conn.execute(
                "SELECT status FROM system_optimization_suggestions WHERE suggestion_id = 1"
            ).fetchone()[0]
            conn.close()
        finally:
            os.unlink(db_path)

        self.assertEqual(200, response.status_code)
        self.assertEqual("New", status)
        self.assertIn(b"Invalid suggestion status", response.data)


if __name__ == "__main__":
    unittest.main()
