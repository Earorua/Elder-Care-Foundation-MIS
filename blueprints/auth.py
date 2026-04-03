from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from db import query_db, execute_db

auth_bp = Blueprint('auth', __name__)


def role_required(*roles):
    """Decorator: stack after @login_required. Redirects if user lacks role."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.has_role(*roles):
                flash('Insufficient permissions to access this page', 'warning')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator


class User(UserMixin):
    def __init__(self, row):
        self.id = row['user_id']
        self.user_name = row['user_name']
        self.email = row['email']
        self.role = row['role'] if 'role' in row.keys() else 'viewer'
        self.is_active_flag = row['is_active']

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def has_role(self, *roles):
        return self.role in roles or self.role == 'admin'


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        row = query_db(
            'SELECT user_id, user_name, password, email, role, is_active FROM "User" WHERE user_name = ?',
            [username], one=True
        )
        if row and check_password_hash(row['password'], password):
            if not row['is_active']:
                flash('Account has been disabled', 'danger')
                return render_template('auth/login.html')
            user = User(row)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        flash('Incorrect username or password', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('auth.login'))


# ── User Management (admin only) ──────────────────────

VALID_ROLES = ['admin', 'finance', 'event_coordinator', 'viewer']


@auth_bp.route('/users')
@login_required
@role_required('admin')
def users_list():
    users = query_db('SELECT user_id, user_name, email, role, is_active FROM "User" ORDER BY user_id')
    return render_template('auth/users.html', users=users, roles=VALID_ROLES)


@auth_bp.route('/users/add', methods=['POST'])
@login_required
@role_required('admin')
def users_add():
    user_name = request.form['user_name'].strip()
    existing = query_db('SELECT user_id FROM "User" WHERE user_name = ?', [user_name], one=True)
    if existing:
        flash('Username already exists', 'danger')
        return redirect(url_for('auth.users_list'))
    execute_db(
        'INSERT INTO "User" (user_name, password, email, is_active, role, created_date, updated_date) '
        'VALUES (?, ?, ?, 1, ?, date("now"), date("now"))',
        [user_name, generate_password_hash(request.form['password']),
         request.form.get('email', ''), request.form['role']]
    )
    flash('User added successfully', 'success')
    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/edit/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def users_edit(id):
    role = request.form['role']
    email = request.form.get('email', '')
    is_active = 1 if request.form.get('is_active') else 0
    password = request.form.get('password', '').strip()
    if password:
        execute_db(
            'UPDATE "User" SET email=?, role=?, is_active=?, password=?, updated_date=date("now") WHERE user_id=?',
            [email, role, is_active, generate_password_hash(password), id]
        )
    else:
        execute_db(
            'UPDATE "User" SET email=?, role=?, is_active=?, updated_date=date("now") WHERE user_id=?',
            [email, role, is_active, id]
        )
    flash('User updated successfully', 'success')
    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def users_delete(id):
    if id == current_user.id:
        flash('Cannot delete your own account', 'danger')
        return redirect(url_for('auth.users_list'))
    execute_db('DELETE FROM "User" WHERE user_id=?', [id])
    flash('User deleted successfully', 'success')
    return redirect(url_for('auth.users_list'))
