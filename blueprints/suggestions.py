import secrets
from hmac import compare_digest

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from blueprints.auth import role_required
from db import execute_db, get_db, query_db


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


def _get_admin_csrf_token():
    token = session.get("suggestions_admin_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["suggestions_admin_csrf_token"] = token
    return token


def _valid_admin_csrf_token(token):
    session_token = session.get("suggestions_admin_csrf_token")
    if not token or not session_token:
        return False
    return compare_digest(token, session_token)


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
            current_app.logger.exception("Failed to submit system optimization suggestion")
            flash("Failed to submit suggestion", "danger")

    return render_template(
        "suggestions/submit.html",
        categories=CATEGORIES,
        priorities=PRIORITIES,
        form_data={},
    )


@suggestions_bp.route("/admin/suggestions")
@login_required
@role_required("admin")
def admin_suggestions():
    return render_template(
        "suggestions/admin_list.html",
        suggestions=list_suggestions(),
        statuses=STATUSES,
        csrf_token=_get_admin_csrf_token(),
    )


@suggestions_bp.route("/admin/suggestions/<int:suggestion_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def update_status(suggestion_id):
    status = (request.form.get("status") or "").strip()
    admin_notes = (request.form.get("admin_notes") or "").strip()
    csrf_token = request.form.get("csrf_token")

    if not _valid_admin_csrf_token(csrf_token):
        flash("Invalid request token", "danger")
        return redirect(url_for("suggestions.admin_suggestions"))

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
