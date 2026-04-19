# System Optimization Suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a login-required system optimization suggestion workflow where any active user can submit suggestions and administrators can review and update them in the main site.

**Architecture:** Add a focused `suggestions` Flask blueprint with shared constants, validation, persistence helpers, public authenticated submission routes, and admin-only review routes. Store suggestions in a new SQLite table created during app startup, then expose the data through a standalone submission template and a main-site admin template.

**Tech Stack:** Flask, Flask-Login, direct SQLite access through `db.py`, Jinja2 templates, Bootstrap 5, existing `static/css/style.css`, existing `static/js/i18n.js`, and `unittest`.

---

## Pre-Flight Notes

The current working tree may contain unrelated staged and unstaged changes. Do not revert them. Every commit command below uses explicit paths and `git commit --only` so unrelated staged files stay out of these commits.

Run before starting:

```powershell
git status --short --branch
```

Expected: note any unrelated changes and leave them alone.

## File Structure

- Create `blueprints/suggestions.py`: suggestion constants, table creation helper, form validation, insert helper, admin status helper, and routes.
- Modify `app.py`: import/register `suggestions_bp` and call `ensure_suggestions_table(db)` during startup.
- Create `templates/suggestions/submit.html`: standalone authenticated suggestion submission page that reuses shared CSS, logo, Bootstrap, Bootstrap Icons, and `i18n.js`.
- Create `templates/suggestions/admin_list.html`: admin-only list/status page extending `base.html`.
- Modify `templates/base.html`: add the admin-only sidebar link under Administration.
- Modify `static/js/i18n.js`: add new user-facing i18n keys.
- Create `tests/test_suggestions.py`: route, permission, persistence, template hook, and i18n regression tests.
- Modify `USER_MANUAL.md`: document where users submit suggestions and where admins review them.
- Modify `CLAUDE.md`: record the new blueprint/table/routes for future agents.

---

### Task 1: Suggestion Table And Constants

**Files:**
- Create: `blueprints/suggestions.py`
- Create: `tests/test_suggestions.py`

- [ ] **Step 1: Write the failing data model test**

Create `tests/test_suggestions.py` with this content:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: FAIL or ERROR because `blueprints.suggestions` does not exist.

- [ ] **Step 3: Add the minimal blueprint module and table helper**

Create `blueprints/suggestions.py` with this content:

```python
from flask import Blueprint


suggestions_bp = Blueprint("suggestions", __name__)

CATEGORIES = (
    "Functionality",
    "Usability",
    "Performance",
    "Data Quality",
    "Security",
    "Reporting",
    "Other",
)
PRIORITIES = ("Low", "Medium", "High", "Urgent")
STATUSES = ("New", "Reviewed", "Planned", "Resolved")


def ensure_suggestions_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS system_optimization_suggestions (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitter_user_id INTEGER NOT NULL,
            submitter_name TEXT NOT NULL,
            submitter_role TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'New',
            admin_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_system_optimization_suggestions_created "
        "ON system_optimization_suggestions(created_at)"
    )
    db.commit()
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

Run:

```powershell
git add blueprints/suggestions.py tests/test_suggestions.py
git commit --only blueprints/suggestions.py tests/test_suggestions.py -m "feat: add suggestions data model"
```

Expected: commit includes only `blueprints/suggestions.py` and `tests/test_suggestions.py`.

---

### Task 2: Authenticated Submission Route

**Files:**
- Modify: `tests/test_suggestions.py`
- Modify: `blueprints/suggestions.py`
- Modify: `app.py`
- Create: `templates/suggestions/submit.html`

- [ ] **Step 1: Add failing submission route and persistence tests**

Append these test methods inside `class SuggestionDataModelTests(unittest.TestCase):` in `tests/test_suggestions.py`:

```python
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
        self.assertEqual("Please add saved filter presets to the dashboard.", row["content"])
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: FAIL because `/suggestions` is not registered and app startup does not create the table.

- [ ] **Step 3: Implement validation, insert helper, and submission route**

Replace `blueprints/suggestions.py` with this content:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from db import execute_db


suggestions_bp = Blueprint("suggestions", __name__)

CATEGORIES = (
    "Functionality",
    "Usability",
    "Performance",
    "Data Quality",
    "Security",
    "Reporting",
    "Other",
)
PRIORITIES = ("Low", "Medium", "High", "Urgent")
STATUSES = ("New", "Reviewed", "Planned", "Resolved")
TITLE_MAX_LENGTH = 120
CONTENT_MAX_LENGTH = 2000


def ensure_suggestions_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS system_optimization_suggestions (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitter_user_id INTEGER NOT NULL,
            submitter_name TEXT NOT NULL,
            submitter_role TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'New',
            admin_notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_system_optimization_suggestions_created "
        "ON system_optimization_suggestions(created_at)"
    )
    db.commit()


def validate_suggestion_form(form):
    title = (form.get("title") or "").strip()
    content = (form.get("content") or "").strip()
    category = (form.get("category") or "").strip()
    priority = (form.get("priority") or "").strip()
    errors = []

    if not title:
        errors.append("Please enter a suggestion title")
    elif len(title) > TITLE_MAX_LENGTH:
        errors.append("Suggestion title must be 120 characters or fewer")

    if not content:
        errors.append("Please enter suggestion details")
    elif len(content) > CONTENT_MAX_LENGTH:
        errors.append("Suggestion details must be 2000 characters or fewer")

    if category not in CATEGORIES:
        errors.append("Please select a valid suggestion category")

    if priority not in PRIORITIES:
        errors.append("Please select a valid suggestion priority")

    return {
        "title": title,
        "category": category,
        "priority": priority,
        "content": content,
    }, errors


def insert_suggestion(data, user):
    execute_db(
        "INSERT INTO system_optimization_suggestions "
        "(submitter_user_id, submitter_name, submitter_role, title, category, "
        "priority, content, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'New', datetime('now'), datetime('now'))",
        [
            user.id,
            user.user_name,
            user.role,
            data["title"],
            data["category"],
            data["priority"],
            data["content"],
        ],
    )


@suggestions_bp.route("/suggestions", methods=["GET", "POST"])
@login_required
def submit_suggestion():
    if request.method == "POST":
        data, errors = validate_suggestion_form(request.form)
        if errors:
            for error in errors:
                flash(error, "warning")
            return render_template(
                "suggestions/submit.html",
                categories=CATEGORIES,
                priorities=PRIORITIES,
                form_data=data,
            )

        try:
            insert_suggestion(data, current_user)
            flash("Suggestion submitted successfully", "success")
            return redirect(url_for("suggestions.submit_suggestion"))
        except Exception:
            flash("Failed to submit suggestion", "danger")

    return render_template(
        "suggestions/submit.html",
        categories=CATEGORIES,
        priorities=PRIORITIES,
        form_data={},
    )
```

- [ ] **Step 4: Register the blueprint and startup table creation**

In `app.py`, add the import with the other blueprint imports:

```python
    from blueprints.suggestions import suggestions_bp
```

Register the blueprint after the existing blueprint registrations:

```python
    app.register_blueprint(suggestions_bp)
```

Inside `_seed_admin()`, after `_ensure_donor_supplier_fields(db)`, add:

```python
    from blueprints.suggestions import ensure_suggestions_table

    ensure_suggestions_table(db)
```

- [ ] **Step 5: Create the standalone submission template**

Create `templates/suggestions/submit.html`:

```jinja2
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title data-i18n="System Optimization Suggestions">System Optimization Suggestions</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/style.css') }}" rel="stylesheet">
  <script src="{{ url_for('static', filename='js/i18n.js') }}"></script>
</head>
<body>
<a href="#suggestion-main" class="skip-link" data-i18n="Skip to main content">Skip to main content</a>
<div class="topbar">
  <a href="{{ url_for('dashboard.index') }}" class="d-flex align-items-center gap-2 text-decoration-none">
    <img src="{{ url_for('static', filename='img/logo.png') }}" alt="Logo" style="width:34px;height:34px;object-fit:contain;">
    <span class="fw-semibold" data-i18n="Elder Care">Elder Care</span>
  </a>
  <div class="topbar-right">
    <button id="langToggleBtn" class="btn btn-sm lang-toggle-btn" onclick="I18n.setLang(I18n.getLang()==='en'?'zh':'en')" title="Switch language">
      <i class="bi bi-translate me-1"></i>中文
    </button>
    <span class="topbar-user-name">{{ current_user.user_name }} · {{ current_user.role }}</span>
    <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('dashboard.index') }}"><i class="bi bi-house-door me-1"></i><span data-i18n="Dashboard">Dashboard</span></a>
    <a class="btn btn-sm btn-outline-secondary" href="{{ url_for('auth.logout') }}"><i class="bi bi-box-arrow-left me-1"></i><span data-i18n="Logout">Logout</span></a>
  </div>
</div>

<main id="suggestion-main" class="content-area" role="main" style="max-width:960px;margin:0 auto;">
  {% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
      <span data-i18n="{{ message }}">{{ message }}</span>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
  {% endif %}
  {% endwith %}

  <div class="page-header">
    <div>
      <h4 class="mb-1"><i class="bi bi-lightbulb me-2"></i><span data-i18n="System Optimization Suggestions">System Optimization Suggestions</span></h4>
      <p class="page-subtitle" data-i18n="Submit improvement ideas for administrators to review.">Submit improvement ideas for administrators to review.</p>
    </div>
    <span class="badge bg-primary"><i class="bi bi-person-check me-1"></i>{{ current_user.user_name }}</span>
  </div>

  <div class="card p-4">
    <form method="post" action="{{ url_for('suggestions.submit_suggestion') }}">
      <div class="mb-3">
        <label class="form-label" for="title" data-i18n="Suggestion Title">Suggestion Title</label>
        <input class="form-control" id="title" name="title" maxlength="120" required
               value="{{ form_data.get('title', '') }}"
               data-i18n-placeholder="Briefly describe the improvement"
               placeholder="Briefly describe the improvement">
      </div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label" for="category" data-i18n="Category">Category</label>
          <select class="form-select" id="category" name="category" required>
            {% for category in categories %}
            <option value="{{ category }}" data-i18n="{{ category }}" {{ 'selected' if form_data.get('category') == category }}>{{ category }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label" for="priority" data-i18n="Priority">Priority</label>
          <select class="form-select" id="priority" name="priority" required>
            {% for priority in priorities %}
            <option value="{{ priority }}" data-i18n="{{ priority }}" {{ 'selected' if form_data.get('priority', 'Medium') == priority }}>{{ priority }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="mt-3 mb-4">
        <label class="form-label" for="content" data-i18n="Suggestion Details">Suggestion Details</label>
        <textarea class="form-control" id="content" name="content" rows="8" maxlength="2000" required
                  data-i18n-placeholder="Describe the problem, expected improvement, and affected workflow"
                  placeholder="Describe the problem, expected improvement, and affected workflow">{{ form_data.get('content', '') }}</textarea>
      </div>
      <button type="submit" class="btn btn-primary">
        <i class="bi bi-send me-1"></i><span data-i18n="Submit Suggestion">Submit Suggestion</span>
      </button>
    </form>
  </div>
</main>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: PASS.

- [ ] **Step 7: Commit this task**

Run:

```powershell
git add app.py blueprints/suggestions.py templates/suggestions/submit.html tests/test_suggestions.py
git commit --only app.py blueprints/suggestions.py templates/suggestions/submit.html tests/test_suggestions.py -m "feat: add authenticated suggestion submission"
```

Expected: commit includes only listed files.

---

### Task 3: Admin Review And Status Updates

**Files:**
- Modify: `tests/test_suggestions.py`
- Modify: `blueprints/suggestions.py`
- Create: `templates/suggestions/admin_list.html`
- Modify: `templates/base.html`

- [ ] **Step 1: Add failing admin route tests**

Append these methods inside `class SuggestionDataModelTests(unittest.TestCase):`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: FAIL because `/admin/suggestions` and the status route do not exist.

- [ ] **Step 3: Add admin helper functions and routes**

In `blueprints/suggestions.py`, update the imports:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from blueprints.auth import role_required
from db import execute_db, get_db, query_db
```

Add these helpers after `insert_suggestion`:

```python
def list_suggestions():
    return query_db(
        "SELECT * FROM system_optimization_suggestions "
        "ORDER BY datetime(created_at) DESC, suggestion_id DESC"
    )


def update_suggestion_status(suggestion_id, status, admin_notes):
    if status not in STATUSES:
        raise ValueError("Invalid suggestion status")

    db = get_db()
    row = db.execute(
        "SELECT suggestion_id FROM system_optimization_suggestions WHERE suggestion_id = ?",
        [suggestion_id],
    ).fetchone()
    if row is None:
        return False

    db.execute(
        "UPDATE system_optimization_suggestions "
        "SET status = ?, admin_notes = ?, updated_at = datetime('now') "
        "WHERE suggestion_id = ?",
        [status, admin_notes, suggestion_id],
    )
    db.commit()
    return True
```

Add these routes after `submit_suggestion`:

```python
@suggestions_bp.route("/admin/suggestions")
@login_required
@role_required("admin")
def admin_suggestions():
    return render_template(
        "suggestions/admin_list.html",
        suggestions=list_suggestions(),
        statuses=STATUSES,
    )


@suggestions_bp.route("/admin/suggestions/<int:suggestion_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def update_status(suggestion_id):
    status = (request.form.get("status") or "").strip()
    admin_notes = (request.form.get("admin_notes") or "").strip()

    try:
        updated = update_suggestion_status(suggestion_id, status, admin_notes)
    except ValueError:
        flash("Invalid suggestion status", "danger")
        return redirect(url_for("suggestions.admin_suggestions"))

    if updated:
        flash("Suggestion status updated", "success")
    else:
        flash("Suggestion not found", "warning")
    return redirect(url_for("suggestions.admin_suggestions"))
```

- [ ] **Step 4: Create the admin list template**

Create `templates/suggestions/admin_list.html`:

```jinja2
{% extends "base.html" %}
{% from "macros/i18n_values.html" import value as i18n_value %}
{% block title %}System Optimization Suggestions - Elder Care MIS{% endblock %}
{% block breadcrumb %}<span data-i18n="System Optimization Suggestions">System Optimization Suggestions</span>{% endblock %}
{% block content %}
<div class="page-header">
  <div>
    <h4 class="mb-1"><i class="bi bi-lightbulb-fill me-2"></i><span data-i18n="System Optimization Suggestions">System Optimization Suggestions</span> <span class="record-count"><i class="bi bi-database"></i>{{ suggestions|length }} <span data-i18n="records">records</span></span></h4>
    <p class="page-subtitle" data-i18n="Review submitted improvement ideas and update their status.">Review submitted improvement ideas and update their status.</p>
  </div>
  <a class="btn btn-outline-primary" href="{{ url_for('suggestions.submit_suggestion') }}"><i class="bi bi-plus-lg me-1"></i><span data-i18n="Submit Suggestion">Submit Suggestion</span></a>
</div>

<div class="table-info-bar">
  <div class="table-search mb-3">
    <div class="input-group" style="max-width:320px;">
      <span class="input-group-text"><i class="bi bi-search"></i></span>
      <input type="text" class="form-control" data-i18n-placeholder="Search suggestions..." placeholder="Search suggestions..." id="tableSearch">
    </div>
  </div>
</div>

{% if suggestions %}
<div class="card p-0">
  <div class="table-responsive">
    <table class="table table-hover mb-0">
      <thead class="table-header">
        <tr>
          <th data-i18n="ID">ID</th>
          <th data-i18n="Suggestion Title">Suggestion Title</th>
          <th data-i18n="Category">Category</th>
          <th data-i18n="Priority">Priority</th>
          <th data-i18n="Status">Status</th>
          <th data-i18n="Submitted By">Submitted By</th>
          <th data-i18n="Role">Role</th>
          <th data-i18n="Submitted Date">Submitted Date</th>
          <th data-i18n="Actions">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for suggestion in suggestions %}
        <tr>
          <td>{{ suggestion.suggestion_id }}</td>
          <td>
            <div class="fw-semibold">{{ suggestion.title }}</div>
            <div class="text-muted" style="white-space:normal;max-width:360px;">{{ suggestion.content }}</div>
            {% if suggestion.admin_notes %}
            <div class="mt-1 small"><span class="fw-semibold" data-i18n="Admin Notes">Admin Notes</span>: {{ suggestion.admin_notes }}</div>
            {% endif %}
          </td>
          <td>{{ i18n_value(suggestion.category) }}</td>
          <td><span class="badge bg-{{ 'danger' if suggestion.priority == 'Urgent' else 'warning' if suggestion.priority == 'High' else 'primary' if suggestion.priority == 'Medium' else 'secondary' }}">{{ i18n_value(suggestion.priority) }}</span></td>
          <td><span class="badge bg-{{ 'success' if suggestion.status == 'Resolved' else 'primary' if suggestion.status == 'Planned' else 'warning' if suggestion.status == 'Reviewed' else 'secondary' }}">{{ i18n_value(suggestion.status) }}</span></td>
          <td>{{ suggestion.submitter_name }}</td>
          <td>{{ suggestion.submitter_role }}</td>
          <td>{{ suggestion.created_at }}</td>
          <td>
            <form method="post" action="{{ url_for('suggestions.update_status', suggestion_id=suggestion.suggestion_id) }}" class="d-flex flex-column gap-2" style="min-width:220px;">
              <select name="status" class="form-select form-select-sm" aria-label="Status">
                {% for status in statuses %}
                <option value="{{ status }}" data-i18n="{{ status }}" {{ 'selected' if suggestion.status == status }}>{{ status }}</option>
                {% endfor %}
              </select>
              <input name="admin_notes" class="form-control form-control-sm" value="{{ suggestion.admin_notes or '' }}" data-i18n-placeholder="Admin Notes" placeholder="Admin Notes">
              <button type="submit" class="btn btn-sm btn-primary"><i class="bi bi-check-lg me-1"></i><span data-i18n="Save">Save</span></button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% else %}
<div class="empty-state">
  <i class="bi bi-lightbulb"></i>
  <h6 data-i18n="No suggestions found">No suggestions found</h6>
  <p data-i18n="Submitted suggestions will appear here.">Submitted suggestions will appear here.</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Add the admin sidebar link**

In `templates/base.html`, under the existing admin link:

```jinja2
      <a class="nav-link" href="{{ url_for('auth.users_list') }}"><i class="bi bi-shield-lock me-2"></i><span data-i18n="User Management">User Management</span></a>
```

add:

```jinja2
      <a class="nav-link" href="{{ url_for('suggestions.admin_suggestions') }}"><i class="bi bi-lightbulb me-2"></i><span data-i18n="System Optimization Suggestions">System Optimization Suggestions</span></a>
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: PASS.

- [ ] **Step 7: Commit this task**

Run:

```powershell
git add blueprints/suggestions.py templates/suggestions/admin_list.html templates/base.html tests/test_suggestions.py
git commit --only blueprints/suggestions.py templates/suggestions/admin_list.html templates/base.html tests/test_suggestions.py -m "feat: add admin suggestion review"
```

Expected: commit includes only listed files.

---

### Task 4: i18n And Template Hooks

**Files:**
- Modify: `tests/test_suggestions.py`
- Modify: `static/js/i18n.js`
- Modify: `templates/suggestions/submit.html`
- Modify: `templates/suggestions/admin_list.html`
- Modify: `templates/base.html`

- [ ] **Step 1: Add failing template and i18n tests**

Append these methods inside `class SuggestionDataModelTests(unittest.TestCase):`:

```python
    def test_templates_expose_i18n_and_shared_style_hooks(self):
        submit = SUBMIT_TEMPLATE.read_text(encoding="utf-8")
        admin = ADMIN_TEMPLATE.read_text(encoding="utf-8")
        base = BASE_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            "static/css/style.css",
            "static/js/i18n.js",
            'id="langToggleBtn"',
            'data-i18n="System Optimization Suggestions"',
            'data-i18n="Submit Suggestion"',
            'data-i18n="Suggestion Title"',
            'data-i18n="Suggestion Details"',
            'data-i18n-placeholder="Briefly describe the improvement"',
            'data-i18n-placeholder="Describe the problem, expected improvement, and affected workflow"',
        ]:
            with self.subTest(template="submit", hook=hook):
                self.assertIn(hook, submit)

        for hook in [
            '{% extends "base.html" %}',
            'data-i18n="System Optimization Suggestions"',
            'data-i18n="Submitted By"',
            'data-i18n="Submitted Date"',
            'data-i18n="Admin Notes"',
            "i18n_value(suggestion.category)",
            "i18n_value(suggestion.priority)",
            "i18n_value(suggestion.status)",
        ]:
            with self.subTest(template="admin", hook=hook):
                self.assertIn(hook, admin)

        self.assertIn("current_user.is_admin", base)
        self.assertIn("suggestions.admin_suggestions", base)

    def test_i18n_contains_suggestion_keys(self):
        i18n = I18N_JS.read_text(encoding="utf-8")

        for key in [
            "System Optimization Suggestions",
            "Submit Suggestion",
            "Suggestion Title",
            "Suggestion Details",
            "Briefly describe the improvement",
            "Describe the problem, expected improvement, and affected workflow",
            "Submit improvement ideas for administrators to review.",
            "Review submitted improvement ideas and update their status.",
            "Category",
            "Priority",
            "Submitted By",
            "Submitted Date",
            "Admin Notes",
            "Functionality",
            "Usability",
            "Performance",
            "Data Quality",
            "Security",
            "Reporting",
            "Other",
            "Low",
            "Medium",
            "High",
            "Urgent",
            "New",
            "Reviewed",
            "Planned",
            "Resolved",
            "Suggestion submitted successfully",
            "Suggestion status updated",
            "Invalid suggestion status",
            "Suggestion not found",
            "Failed to submit suggestion",
            "Please enter a suggestion title",
            "Please enter suggestion details",
            "Please select a valid suggestion category",
            "Please select a valid suggestion priority",
            "No suggestions found",
            "Submitted suggestions will appear here.",
            "Search suggestions...",
        ]:
            with self.subTest(key=key):
                self.assertIn(f"'{key}':", i18n)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: FAIL because `static/js/i18n.js` does not contain all new keys.

- [ ] **Step 3: Add i18n keys**

In `static/js/i18n.js`, inside the `ZH` object near other administration/general labels, add this block without rewriting existing keys:

```javascript
    // System optimization suggestions
    'System Optimization Suggestions': '系统优化建议',
    'Submit Suggestion': '提交建议',
    'Suggestion Title': '建议标题',
    'Suggestion Details': '建议详情',
    'Briefly describe the improvement': '简要描述改进建议',
    'Describe the problem, expected improvement, and affected workflow': '描述问题、期望改进和受影响的流程',
    'Submit improvement ideas for administrators to review.': '提交改进想法，供管理员审核。',
    'Review submitted improvement ideas and update their status.': '查看已提交的改进建议并更新状态。',
    'Submitted By': '提交人',
    'Submitted Date': '提交日期',
    'Admin Notes': '管理员备注',
    'Functionality': '功能',
    'Usability': '易用性',
    'Performance': '性能',
    'Data Quality': '数据质量',
    'Security': '安全',
    'Reporting': '报表',
    'Low': '低',
    'Medium': '中',
    'High': '高',
    'Urgent': '紧急',
    'New': '新建',
    'Suggestion submitted successfully': '建议提交成功',
    'Suggestion status updated': '建议状态已更新',
    'Invalid suggestion status': '无效的建议状态',
    'Suggestion not found': '未找到建议',
    'Failed to submit suggestion': '提交建议失败',
    'Please enter a suggestion title': '请输入建议标题',
    'Please enter suggestion details': '请输入建议详情',
    'Please select a valid suggestion category': '请选择有效的建议分类',
    'Please select a valid suggestion priority': '请选择有效的建议优先级',
    'No suggestions found': '暂无建议',
    'Submitted suggestions will appear here.': '已提交的建议会显示在这里。',
    'Search suggestions...': '搜索建议...',
```

If `Other`, `Category`, `Priority`, `Reviewed`, `Planned`, or `Resolved` already exist, do not duplicate them. If one of those keys is missing, add only the missing key:

```javascript
    'Other': '其他',
    'Category': '分类',
    'Priority': '优先级',
    'Reviewed': '已审核',
    'Planned': '已计划',
    'Resolved': '已解决',
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: PASS.

- [ ] **Step 5: Commit this task**

Run:

```powershell
git add static/js/i18n.js templates/suggestions/submit.html templates/suggestions/admin_list.html templates/base.html tests/test_suggestions.py
git commit --only static/js/i18n.js templates/suggestions/submit.html templates/suggestions/admin_list.html templates/base.html tests/test_suggestions.py -m "feat: add suggestion i18n hooks"
```

Expected: commit includes only listed files.

---

### Task 5: User Documentation And Agent Notes

**Files:**
- Modify: `USER_MANUAL.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `USER_MANUAL.md`**

Add a short section describing:

```markdown
## System Optimization Suggestions

Any logged-in user can open `/suggestions` to submit a system optimization suggestion. The form records the current account automatically, so no contact fields are required.

Administrators can review submitted suggestions from the Administration area under "System Optimization Suggestions". Admins can update each suggestion status to New, Reviewed, Planned, or Resolved and add internal notes.
```

- [ ] **Step 2: Update `CLAUDE.md`**

Add a concise architecture note:

```markdown
## System Optimization Suggestions

- `blueprints/suggestions.py` owns the login-required `/suggestions` submission flow and admin-only `/admin/suggestions` review flow.
- Suggestions are stored in `system_optimization_suggestions`, created at startup by `ensure_suggestions_table(db)`.
- Any authenticated active user can submit suggestions. Only `admin` users can view and update the admin review module.
- The standalone submission page reuses the existing global CSS, logo, Bootstrap assets, and `static/js/i18n.js`.
```

- [ ] **Step 3: Check documentation text is present**

Run:

```powershell
rg -n "System Optimization Suggestions|/suggestions|system_optimization_suggestions" USER_MANUAL.md CLAUDE.md
```

Expected: both files mention the feature and the route/table names.

- [ ] **Step 4: Commit this task**

Run:

```powershell
git add USER_MANUAL.md CLAUDE.md
git commit --only USER_MANUAL.md CLAUDE.md -m "docs: document system optimization suggestions"
```

Expected: commit includes only `USER_MANUAL.md` and `CLAUDE.md`.

---

### Task 6: Full Verification

**Files:**
- No planned edits.

- [ ] **Step 1: Run the targeted test file**

Run:

```powershell
python -m unittest tests.test_suggestions
```

Expected: PASS.

- [ ] **Step 2: Run existing relevant template tests**

Run:

```powershell
python -m unittest tests.test_bi_ui_template tests.test_marital_status_ui tests.test_donor_supplier_fields
```

Expected: PASS.

- [ ] **Step 3: Run the full suite**

Run:

```powershell
python -m unittest discover
```

Expected: PASS.

- [ ] **Step 4: Inspect changed files**

Run:

```powershell
git status --short --branch
git diff --stat
```

Expected: only expected feature files remain modified or committed. Existing unrelated changes may still be present and must not be reverted.

- [ ] **Step 5: Manual smoke test**

Run:

```powershell
python app.py
```

Open `http://127.0.0.1:5000/login`, log in as `viewer` / `viewer123`, open `http://127.0.0.1:5000/suggestions`, submit a suggestion, then log in as `admin` / `admin123` and open `http://127.0.0.1:5000/admin/suggestions`.

Expected:

- Viewer can submit.
- Admin can see the suggestion.
- Viewer cannot access `/admin/suggestions`.
- Language toggle is visible on `/suggestions`.
- Main site visual styling remains unchanged.
