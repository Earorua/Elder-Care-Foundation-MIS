from flask import Flask
from flask_login import LoginManager
import config
import db as database

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    database.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in first'

    from blueprints.auth import auth_bp, User
    from blueprints.dashboard import dashboard_bp
    from blueprints.donations import donations_bp
    from blueprints.personnel import personnel_bp
    from blueprints.gifts import gifts_bp
    from blueprints.events import events_bp
    from blueprints.finance import finance_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(gifts_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(finance_bp)

    @login_manager.user_loader
    def load_user(user_id):
        row = database.query_db(
            'SELECT user_id, user_name, email, role, is_active FROM "User" WHERE user_id = ?',
            [user_id], one=True
        )
        if row:
            return User(row)
        return None

    with app.app_context():
        _seed_admin()

    return app


def _seed_admin():
    from werkzeug.security import generate_password_hash
    from db import get_db, query_db

    # Ensure role column exists
    db = get_db()
    cols = [r[1] for r in db.execute('PRAGMA table_info("User")').fetchall()]
    if 'role' not in cols:
        db.execute('ALTER TABLE "User" ADD COLUMN role TEXT DEFAULT "viewer"')
        db.commit()

    existing = query_db('SELECT user_id FROM "User" WHERE user_name = ?', ['admin'], one=True)
    if not existing:
        db.execute(
            'INSERT INTO "User" (user_name, password, email, is_active, role, created_date, updated_date) '
            'VALUES (?, ?, ?, 1, ?, date("now"), date("now"))',
            ['admin', generate_password_hash('admin123'), 'admin@eldercare.org', 'admin']
        )
        db.commit()
    else:
        # Ensure admin has admin role and hashed password
        db.execute('UPDATE "User" SET role = ?, password = ? WHERE user_name = ?',
                   ['admin', generate_password_hash('admin123'), 'admin'])
        db.commit()

    # Seed additional role users
    seed_users = [
        ('finance_user', 'finance123', 'finance@eldercare.org', 'finance'),
        ('coordinator', 'coord123', 'coordinator@eldercare.org', 'event_coordinator'),
        ('viewer', 'viewer123', 'viewer@eldercare.org', 'viewer'),
    ]
    for uname, pwd, email, role in seed_users:
        exists = query_db('SELECT user_id FROM "User" WHERE user_name = ?', [uname], one=True)
        if not exists:
            db.execute(
                'INSERT INTO "User" (user_name, password, email, is_active, role, created_date, updated_date) '
                'VALUES (?, ?, ?, 1, ?, date("now"), date("now"))',
                [uname, generate_password_hash(pwd), email, role]
            )
    db.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
