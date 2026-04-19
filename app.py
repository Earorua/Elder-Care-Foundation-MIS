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
    login_manager.login_message_category = 'warning'

    from blueprints.auth import auth_bp, User
    from blueprints.dashboard import dashboard_bp
    from blueprints.donations import donations_bp
    from blueprints.personnel import personnel_bp
    from blueprints.gifts import gifts_bp
    from blueprints.events import events_bp
    from blueprints.finance import finance_bp
    from blueprints.bi import bi_bp
    from blueprints.agent import agent_bp
    from blueprints.suggestions import suggestions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(gifts_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(bi_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(suggestions_bp)

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

    db = get_db()
    cols = [r[1] for r in db.execute('PRAGMA table_info("User")').fetchall()]
    if 'role' not in cols:
        db.execute('ALTER TABLE "User" ADD COLUMN role TEXT DEFAULT "viewer"')
        db.commit()

    _ensure_donor_supplier_fields(db)
    from blueprints.suggestions import ensure_suggestions_table

    ensure_suggestions_table(db)

    existing = query_db('SELECT user_id FROM "User" WHERE user_name = ?', ['admin'], one=True)
    if not existing:
        db.execute(
            'INSERT INTO "User" (user_name, password, email, is_active, role, created_date, updated_date) '
            'VALUES (?, ?, ?, 1, ?, date("now"), date("now"))',
            ['admin', generate_password_hash('admin123'), 'admin@eldercare.org', 'admin']
        )
        db.commit()
    else:
        db.execute(
            'UPDATE "User" SET role = ?, password = ? WHERE user_name = ?',
            ['admin', generate_password_hash('admin123'), 'admin']
        )
        db.commit()

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

    gift_count = query_db('SELECT COUNT(*) as cnt FROM gifts', one=True)
    if gift_count['cnt'] == 0:
        seed_gifts = [
            ('Chao Feng & Maui: The Last Adventure', 'Storybook', 10.0,
             "Illustrated children's storybook (print edition) - the tale of Chao Feng the dragon and Maui the demigod",
             200, 30, 1),
            ('Chao Feng & Maui: Digital Edition', 'Storybook', 0.0,
             'Digital version of the storybook (PDF & EPUB) - included with every donation',
             9999, 100, 1),
            ('Chao Feng & Maui: Animated Short DVD', 'Media', 5.0,
             '10-minute animated adaptation of the storybook on DVD',
             150, 20, 1),
            ('Campaign Postcard Set', 'Promotional', 2.5,
             'Set of 4 postcards featuring Chao Feng & Maui illustrations by Buck Steel',
             500, 50, 1),
            ('Donor Thank-You Kit', 'Donor Kit', 15.0,
             'Gift package: print storybook + postcard set + branded envelope for donors',
             120, 20, 1),
            ('Campaign Poster', 'Promotional', 3.0,
             'Promotional poster showcasing the Chao Feng & Maui book series',
             300, 40, 1),
            ('Chao Feng & Maui Picture Book (Chinese Edition)', 'Storybook', 10.0,
             "Chinese-language illustrated edition of the children's storybook",
             100, 15, 1),
            ('Social Media Banner Pack', 'Promotional', 0.0,
             'Digital banner assets for social media outreach and donor campaigns',
             9999, 100, 1),
        ]
        for gname, gtype, cost, desc, stock, min_stock, active in seed_gifts:
            db.execute(
                'INSERT INTO gifts (gift_name, gift_type, unit_cost, description, '
                'current_stock, min_stock_level, is_active, created_date) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, date("now"))',
                [gname, gtype, cost, desc, stock, min_stock, active]
            )
        db.commit()


def _table_columns(db, table_name):
    return [row[1] for row in db.execute(f'PRAGMA table_info("{table_name}")').fetchall()]


def _ensure_donor_supplier_fields(db):
    donor_columns = _table_columns(db, 'donors')
    if donor_columns and 'type' not in donor_columns:
        db.execute("ALTER TABLE donors ADD COLUMN type TEXT DEFAULT 'Person'")
    if donor_columns:
        db.execute("UPDATE donors SET type = 'Person' WHERE type IS NULL OR type = ''")

    supplier_columns = _table_columns(db, 'suppliers')
    if supplier_columns and 'contact_email' not in supplier_columns:
        db.execute("ALTER TABLE suppliers ADD COLUMN contact_email TEXT")
    if supplier_columns:
        supplier_emails = {
            'Pacific Print House': 'keoni.nakamura@pacificprinthouse.org',
            'Buck Steel Illustrations': 'buck.steel@steelartstudio.org',
            'Sunrise Animation Studio': 'amy.chen@sunriseanimationstudio.org',
            'Campus Copy & Design': 'jordan.lee@campuscopydesign.org',
        }
        for supplier_name, contact_email in supplier_emails.items():
            db.execute(
                'UPDATE suppliers SET contact_email = ? '
                'WHERE supplier_name = ? AND (contact_email IS NULL OR contact_email = "")',
                [contact_email, supplier_name]
            )
    db.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
