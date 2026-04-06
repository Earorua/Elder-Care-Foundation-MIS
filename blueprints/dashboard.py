from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from db import query_db

dashboard_bp = Blueprint('dashboard', __name__)

# ── 50 US States + DC (code → name) ──────────────────────────
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
}


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    stats = {
        'total_donations': query_db('SELECT COALESCE(SUM(amount),0) as v FROM donations', one=True)['v'],
        'donor_count': query_db('SELECT COUNT(*) as v FROM donors', one=True)['v'],
        'event_count': query_db('SELECT COUNT(*) as v FROM events', one=True)['v'],
        'person_count': query_db('SELECT COUNT(*) as v FROM persons', one=True)['v'],
        'employee_count': query_db("SELECT COUNT(*) as v FROM persons WHERE person_type='Employee'", one=True)['v'],
        'volunteer_count': query_db("SELECT COUNT(*) as v FROM persons WHERE person_type='Volunteer'", one=True)['v'],
    }
    # ── Finance summary for quick-access cards ──
    total_donations = stats['total_donations']
    total_grants = query_db('SELECT COALESCE(SUM(amount),0) as v FROM grants', one=True)['v']
    total_other = query_db('SELECT COALESCE(SUM(amount),0) as v FROM other_income', one=True)['v']
    total_payments = query_db('SELECT COALESCE(SUM(amount),0) as v FROM payments', one=True)['v']
    total_delivery = query_db('SELECT COALESCE(SUM(delivery_fee),0) as v FROM delivery', one=True)['v']
    total_gift_cost = query_db(
        'SELECT COALESCE(SUM(b.batch_quantity * g.unit_cost),0) as v '
        'FROM gift_batch b JOIN gifts g ON b.gift_id = g.gift_id', one=True)['v']
    finance = {
        'total_revenue': total_donations + total_grants + total_other,
        'total_expenses': total_payments + total_delivery + total_gift_cost,
    }
    finance['net_income'] = finance['total_revenue'] - finance['total_expenses']

    # ── Schedule monitor stats ──
    upcoming_events = query_db(
        "SELECT COUNT(*) as v FROM events WHERE status IN ('planned','active')", one=True)['v']
    upcoming_schedules = query_db(
        "SELECT COUNT(*) as v FROM schedules WHERE status = 'scheduled'", one=True)['v']
    schedule_stats = {
        'upcoming_events': upcoming_events,
        'upcoming_schedules': upcoming_schedules,
    }

    return render_template('dashboard/index.html', stats=stats,
                           finance=finance, schedule_stats=schedule_stats)


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
        "SELECT bracket, cnt FROM ("
        "  SELECT CASE WHEN age<30 THEN '<30' WHEN age<50 THEN '30-49' "
        "  WHEN age<70 THEN '50-69' ELSE '70+' END as bracket, "
        "  COUNT(*) as cnt, "
        "  CASE WHEN age<30 THEN 1 WHEN age<50 THEN 2 "
        "  WHEN age<70 THEN 3 ELSE 4 END as sort_order "
        "  FROM donors GROUP BY bracket"
        ") ORDER BY sort_order"
    )
    return jsonify(labels=[r['bracket'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/location')
@login_required
def chart_location():
    rows = query_db("SELECT location, COUNT(*) as cnt FROM donors GROUP BY location ORDER BY cnt DESC LIMIT 10")
    return jsonify(labels=[r['location'] for r in rows], data=[r['cnt'] for r in rows])


@dashboard_bp.route('/api/charts/location_map')
@login_required
def chart_location_map():
    """Return donor count per US state for the SVG map."""
    rows = query_db("SELECT location, COUNT(*) as cnt FROM donors GROUP BY location")
    state_data = {}
    for r in rows:
        loc = r['location']
        # Try to match location to a state code
        if loc in US_STATES:
            state_data[loc] = state_data.get(loc, 0) + r['cnt']
        else:
            # Try matching by full state name
            for code, name in US_STATES.items():
                if name == loc:
                    state_data[code] = state_data.get(code, 0) + r['cnt']
                    break
            else:
                # Try matching city names to states (legacy data)
                city_to_state = {
                    'New York': 'NY', 'Los Angeles': 'CA', 'Chicago': 'IL',
                    'Houston': 'TX', 'Phoenix': 'AZ', 'Philadelphia': 'PA',
                    'San Antonio': 'TX', 'San Diego': 'CA', 'Dallas': 'TX',
                    'San Jose': 'CA',
                }
                if loc in city_to_state:
                    code = city_to_state[loc]
                    state_data[code] = state_data.get(code, 0) + r['cnt']
    return jsonify(state_data=state_data, state_names=US_STATES)


@dashboard_bp.route('/api/charts/gift_distribution')
@login_required
def chart_gift_distribution():
    """Gift distribution data: by gift name, split by free vs donated."""
    rows = query_db(
        "SELECT g.gift_name, "
        "SUM(CASE WHEN gd.is_free=1 THEN gd.quantity ELSE 0 END) as free_qty, "
        "SUM(CASE WHEN gd.is_free=0 THEN gd.quantity ELSE 0 END) as donated_qty "
        "FROM gift_distribution gd "
        "LEFT JOIN gift_batch gb ON gd.batch_id=gb.batch_id "
        "LEFT JOIN gifts g ON gb.gift_id=g.gift_id "
        "GROUP BY g.gift_name ORDER BY (free_qty+donated_qty) DESC"
    )
    return jsonify(
        labels=[r['gift_name'] for r in rows],
        free=[r['free_qty'] for r in rows],
        donated=[r['donated_qty'] for r in rows]
    )


@dashboard_bp.route('/api/charts/event_progress')
@login_required
def chart_event_progress():
    rows = query_db("SELECT event_name, target_amount, actual_amount FROM events WHERE target_amount > 0")
    return jsonify(
        labels=[r['event_name'] for r in rows],
        target=[r['target_amount'] for r in rows],
        actual=[r['actual_amount'] for r in rows]
    )
