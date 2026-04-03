from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from db import query_db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    stats = {
        'total_donations': query_db('SELECT COALESCE(SUM(amount),0) as v FROM donations', one=True)['v'],
        'donor_count': query_db('SELECT COUNT(*) as v FROM donors', one=True)['v'],
        'event_count': query_db('SELECT COUNT(*) as v FROM events', one=True)['v'],
        'person_count': query_db('SELECT COUNT(*) as v FROM persons', one=True)['v'],
    }
    return render_template('dashboard/index.html', stats=stats)


@dashboard_bp.route('/api/charts/monthly_donations')
@login_required
def chart_monthly_donations():
    rows = query_db(
        "SELECT strftime('%Y-%m', donation_date) as month, SUM(amount) as total "
        "FROM donations GROUP BY month ORDER BY month"
    )
    return jsonify(labels=[r['month'] for r in rows], data=[r['total'] for r in rows])


@dashboard_bp.route('/api/charts/donation_types')
@login_required
def chart_donation_types():
    rows = query_db(
        "SELECT donation_type, COUNT(*) as cnt FROM donations GROUP BY donation_type"
    )
    return jsonify(labels=[r['donation_type'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/gender')
@login_required
def chart_gender():
    rows = query_db("SELECT gender, COUNT(*) as cnt FROM donors GROUP BY gender")
    return jsonify(labels=[r['gender'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/age')
@login_required
def chart_age():
    rows = query_db(
        "SELECT CASE WHEN age<30 THEN '<30' WHEN age<50 THEN '30-49' "
        "WHEN age<70 THEN '50-69' ELSE '70+' END as bracket, COUNT(*) as cnt "
        "FROM donors GROUP BY bracket"
    )
    return jsonify(labels=[r['bracket'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/location')
@login_required
def chart_location():
    rows = query_db("SELECT location, COUNT(*) as cnt FROM donors GROUP BY location ORDER BY cnt DESC LIMIT 10")
    return jsonify(labels=[r['location'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/event_progress')
@login_required
def chart_event_progress():
    rows = query_db("SELECT event_name, target_amount, actual_amount FROM events WHERE target_amount > 0")
    return jsonify(
        labels=[r['event_name'] for r in rows],
        target=[r['target_amount'] for r in rows],
        actual=[r['actual_amount'] for r in rows]
    )
