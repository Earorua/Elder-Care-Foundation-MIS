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
