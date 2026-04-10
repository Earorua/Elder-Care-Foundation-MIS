from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from db import query_db
from blueprints.auth import role_required

bi_bp = Blueprint('bi', __name__)

# ---------------------------------------------------------------------------
# Whitelist definitions — all field references are validated against these
# ---------------------------------------------------------------------------

# Filters: name -> {label, type, sql_expr, options_query or options list}
FILTER_DEFS = {
    # Donor filters
    'donor_age':        {'label': 'Donor Age',        'domain': 'donor', 'type': 'range',  'sql': 'dn.age'},
    'donor_gender':     {'label': 'Donor Gender',     'domain': 'donor', 'type': 'enum',   'sql': 'dn.gender',
                         'options': ['Male', 'Female', 'Other']},
    'donor_location':   {'label': 'Donor Location',   'domain': 'donor', 'type': 'enum',   'sql': 'dn.location',
                         'options_query': "SELECT DISTINCT location FROM donors WHERE location != '' ORDER BY location"},
    'donation_amount':  {'label': 'Donation Amount',  'domain': 'donor', 'type': 'range',  'sql': 'd.amount'},
    'donation_type':    {'label': 'Donation Type',    'domain': 'donor', 'type': 'enum',   'sql': 'd.donation_type',
                         'options': ['Cash', 'Check', 'Wire Transfer', 'Credit Card', 'In-Kind']},
    'donation_date':    {'label': 'Donation Date',    'domain': 'donor', 'type': 'daterange', 'sql': 'd.donation_date'},
    'tax_deductible':   {'label': 'Tax Deductible',   'domain': 'donor', 'type': 'bool',   'sql': 'd.is_tax_deductible'},
    # Person filters
    'person_type':      {'label': 'Person Type',      'domain': 'person', 'type': 'enum',  'sql': 'p.person_type',
                         'options': ['Volunteer', 'Staff', 'Contractor', 'Intern']},
    'person_role':      {'label': 'Person Role',      'domain': 'person', 'type': 'enum',  'sql': 'p.role_name',
                         'options_query': "SELECT DISTINCT role_name FROM persons WHERE role_name != '' ORDER BY role_name"},
    'person_status':    {'label': 'Person Status',    'domain': 'person', 'type': 'enum',  'sql': 'p.status',
                         'options': ['Active', 'Inactive', 'On Leave']},
    'person_gender':    {'label': 'Person Gender',    'domain': 'person', 'type': 'enum',  'sql': 'p.gender',
                         'options': ['Male', 'Female', 'Other']},
    'hire_date':        {'label': 'Hire Date',        'domain': 'person', 'type': 'daterange', 'sql': 'p.hire_date'},
    'payment_amount':   {'label': 'Payment Amount',   'domain': 'person', 'type': 'range',  'sql': 'pay.amount'},
    # Event filters
    'event_type':       {'label': 'Event Type',       'domain': 'event', 'type': 'enum',   'sql': 'e.event_type',
                         'options_query': "SELECT DISTINCT event_type FROM events WHERE event_type != '' ORDER BY event_type"},
    'event_status':     {'label': 'Event Status',     'domain': 'event', 'type': 'enum',   'sql': 'e.status',
                         'options': ['Planned', 'Ongoing', 'Completed', 'Cancelled']},
    'event_location':   {'label': 'Event Location',   'domain': 'event', 'type': 'enum',   'sql': 'e.location',
                         'options_query': "SELECT DISTINCT location FROM events WHERE location != '' ORDER BY location"},
    'event_date':       {'label': 'Event Date',       'domain': 'event', 'type': 'daterange', 'sql': 'e.start_date'},
    'target_amount':    {'label': 'Target Amount',    'domain': 'event', 'type': 'range',  'sql': 'e.target_amount'},
    # Gift filters
    'gift_type':        {'label': 'Gift Type',        'domain': 'gift', 'type': 'enum',   'sql': 'g.gift_type',
                         'options_query': "SELECT DISTINCT gift_type FROM gifts WHERE gift_type != '' ORDER BY gift_type"},
    'gift_active':      {'label': 'Gift Active',      'domain': 'gift', 'type': 'bool',   'sql': 'g.is_active'},
    'unit_cost':        {'label': 'Unit Cost',        'domain': 'gift', 'type': 'range',  'sql': 'g.unit_cost'},
    'is_free':          {'label': 'Free Distribution','domain': 'gift', 'type': 'bool',   'sql': 'gd.is_free'},
    # Finance filters
    'source_type':      {'label': 'Source Type',      'domain': 'finance', 'type': 'enum',  'sql': 'f.source_type',
                         'options': ['Grant', 'Other']},
    'finance_amount':   {'label': 'Amount',           'domain': 'finance', 'type': 'range', 'sql': 'f.amount'},
    'finance_date':     {'label': 'Received Date',    'domain': 'finance', 'type': 'daterange', 'sql': 'f.received'},
    # Schedule filters
    'shift_date':       {'label': 'Shift Date',       'domain': 'schedule', 'type': 'daterange', 'sql': 's.shift_date'},
    'schedule_status':  {'label': 'Status',           'domain': 'schedule', 'type': 'enum',  'sql': 's.status',
                         'options': ['Scheduled', 'In Progress', 'Completed', 'Absent']},
    'is_absent_filter': {'label': 'Absent',           'domain': 'schedule', 'type': 'bool',  'sql': 's.is_absent'},
    'overtime':         {'label': 'Overtime (hrs)',    'domain': 'schedule', 'type': 'range', 'sql': 's.overtime'},
}

# Dimensions: name -> {label, sql_expr, domain}
DIMENSION_DEFS = {
    'donor_gender':     {'label': 'Donor Gender',     'domain': 'donor',  'sql': 'dn.gender',
                         'alias': 'donor_gender'},
    'donor_location':   {'label': 'Donor Location',   'domain': 'donor',  'sql': 'dn.location',
                         'alias': 'donor_location'},
    'donor_age_group':  {'label': 'Donor Age Group',  'domain': 'donor',
                         'sql': "CASE WHEN dn.age < 35 THEN 'Under 35' WHEN dn.age < 60 THEN '35–59' WHEN dn.age < 80 THEN '60–79' ELSE '80+' END",
                         'alias': 'donor_age_group'},
    'donation_type':    {'label': 'Donation Type',    'domain': 'donor',  'sql': 'd.donation_type',
                         'alias': 'donation_type'},
    'donation_year':    {'label': 'Donation Year',    'domain': 'donor',  'sql': "strftime('%Y', d.donation_date)",
                         'alias': 'donation_year'},
    'tax_deductible':   {'label': 'Tax Deductible',   'domain': 'donor',
                         'sql': "CASE d.is_tax_deductible WHEN 1 THEN 'Yes' ELSE 'No' END",
                         'alias': 'tax_deductible'},
    'person_type':      {'label': 'Person Type',      'domain': 'person', 'sql': 'p.person_type',
                         'alias': 'person_type'},
    'person_role':      {'label': 'Person Role',      'domain': 'person', 'sql': 'p.role_name',
                         'alias': 'person_role'},
    'person_status':    {'label': 'Person Status',    'domain': 'person', 'sql': 'p.status',
                         'alias': 'person_status'},
    'person_gender':    {'label': 'Person Gender',    'domain': 'person', 'sql': 'p.gender',
                         'alias': 'person_gender'},
    'payment_type':     {'label': 'Payment Type',     'domain': 'person', 'sql': 'pay.payment_type',
                         'alias': 'payment_type'},
    # Event dimensions
    'event_type':       {'label': 'Event Type',       'domain': 'event',  'sql': 'e.event_type',
                         'alias': 'event_type'},
    'event_status':     {'label': 'Event Status',     'domain': 'event',  'sql': 'e.status',
                         'alias': 'event_status'},
    'event_location':   {'label': 'Event Location',   'domain': 'event',  'sql': 'e.location',
                         'alias': 'event_location'},
    'event_year':       {'label': 'Event Year',       'domain': 'event',  'sql': "strftime('%Y', e.start_date)",
                         'alias': 'event_year'},
    # Gift dimensions
    'gift_type':        {'label': 'Gift Type',        'domain': 'gift',  'sql': 'g.gift_type',
                         'alias': 'gift_type'},
    'gift_active_dim':  {'label': 'Gift Active',      'domain': 'gift',
                         'sql': "CASE g.is_active WHEN 1 THEN 'Active' ELSE 'Inactive' END",
                         'alias': 'gift_active'},
    'is_free_dim':      {'label': 'Distribution Type','domain': 'gift',
                         'sql': "CASE gd.is_free WHEN 1 THEN 'Free' ELSE 'Donor Gift' END",
                         'alias': 'distribution_type'},
    # Finance dimensions
    'finance_source_type': {'label': 'Source Type',   'domain': 'finance', 'sql': 'f.source_type',
                            'alias': 'source_type'},
    'finance_source':      {'label': 'Source',        'domain': 'finance', 'sql': 'f.source',
                            'alias': 'source'},
    'finance_year':        {'label': 'Year',          'domain': 'finance',
                            'sql': "strftime('%Y', f.received)",
                            'alias': 'finance_year'},
    # Schedule dimensions
    'schedule_status_dim':  {'label': 'Schedule Status', 'domain': 'schedule', 'sql': 's.status',
                             'alias': 'schedule_status'},
    'is_absent_dim':        {'label': 'Attendance',      'domain': 'schedule',
                             'sql': "CASE s.is_absent WHEN 1 THEN 'Absent' ELSE 'Present' END",
                             'alias': 'attendance'},
    'shift_month':          {'label': 'Shift Month',     'domain': 'schedule',
                             'sql': "strftime('%Y-%m', s.shift_date)",
                             'alias': 'shift_month'},
    'schedule_event_name':  {'label': 'Event',           'domain': 'schedule', 'sql': 'e.event_name',
                             'alias': 'event_name'},
    'schedule_person_type': {'label': 'Person Type',     'domain': 'schedule', 'sql': 'p.person_type',
                             'alias': 'person_type'},
}

# Metrics: name -> {label, sql_expr, domain, format}
METRIC_DEFS = {
    # Donor metrics
    'donor_count':          {'label': 'Donor Count',           'domain': 'donor',
                              'sql': 'COUNT(DISTINCT dn.donor_id)', 'format': 'integer'},
    'pct_of_total_donors':  {'label': '% of Total Donors',     'domain': 'donor',
                              'sql': 'COUNT(DISTINCT dn.donor_id)', 'format': 'percent',
                              'pct_base': 'donor'},
    'total_donation':       {'label': 'Total Donation Amount', 'domain': 'donor',
                              'sql': 'SUM(d.amount)', 'format': 'currency'},
    'avg_donation':         {'label': 'Avg Donation Amount',   'domain': 'donor',
                              'sql': 'AVG(d.amount)', 'format': 'currency'},
    'max_donation':         {'label': 'Max Donation',          'domain': 'donor',
                              'sql': 'MAX(d.amount)', 'format': 'currency'},
    'min_donation':         {'label': 'Min Donation',          'domain': 'donor',
                              'sql': 'MIN(d.amount)', 'format': 'currency'},
    'donation_count':       {'label': 'Donation Count',        'domain': 'donor',
                              'sql': 'COUNT(d.donation_id)', 'format': 'integer'},
    # Person metrics
    'person_count':         {'label': 'Person Count',          'domain': 'person',
                              'sql': 'COUNT(DISTINCT p.person_id)', 'format': 'integer'},
    'pct_of_total_persons': {'label': '% of Total Persons',    'domain': 'person',
                              'sql': 'COUNT(DISTINCT p.person_id)', 'format': 'percent',
                              'pct_base': 'person'},
    'total_payment':        {'label': 'Total Payment Amount',  'domain': 'person',
                              'sql': 'SUM(pay.amount)', 'format': 'currency'},
    'avg_payment':          {'label': 'Avg Payment Amount',    'domain': 'person',
                              'sql': 'AVG(pay.amount)', 'format': 'currency'},
    # Event metrics
    'event_count':       {'label': 'Event Count',           'domain': 'event',
                          'sql': 'COUNT(DISTINCT e.event_id)', 'format': 'integer'},
    'participant_count': {'label': 'Participant Count',     'domain': 'event',
                          'sql': 'COUNT(DISTINCT de.donor_id)', 'format': 'integer'},
    'total_target':      {'label': 'Total Target Amount',   'domain': 'event',
                          'sql': 'SUM(e.target_amount)', 'format': 'currency'},
    'total_actual':      {'label': 'Total Actual Amount',   'domain': 'event',
                          'sql': 'SUM(e.actual_amount)', 'format': 'currency'},
    'avg_target':        {'label': 'Avg Target Amount',     'domain': 'event',
                          'sql': 'AVG(e.target_amount)', 'format': 'currency'},
    'achievement_rate':  {'label': 'Achievement Rate',      'domain': 'event',
                          'sql': 'ROUND(SUM(e.actual_amount)*100.0/NULLIF(SUM(e.target_amount),0), 1)', 'format': 'percent_val'},
    # Gift metrics
    'gift_count':            {'label': 'Gift Count',       'domain': 'gift',
                              'sql': 'COUNT(DISTINCT g.gift_id)', 'format': 'integer'},
    'total_stock':           {'label': 'Total Stock',      'domain': 'gift',
                              'sql': 'SUM(g.current_stock)', 'format': 'integer'},
    'total_distributed':     {'label': 'Total Distributed','domain': 'gift',
                              'sql': 'SUM(gd.quantity)', 'format': 'integer'},
    'total_inventory_value': {'label': 'Inventory Value',  'domain': 'gift',
                              'sql': 'SUM(g.current_stock * g.unit_cost)', 'format': 'currency'},
    'avg_unit_cost':         {'label': 'Avg Unit Cost',    'domain': 'gift',
                              'sql': 'AVG(g.unit_cost)', 'format': 'currency'},
    # Finance metrics
    'income_count':     {'label': 'Income Count',     'domain': 'finance',
                         'sql': 'COUNT(*)', 'format': 'integer'},
    'total_income':     {'label': 'Total Income',     'domain': 'finance',
                         'sql': 'SUM(f.amount)', 'format': 'currency'},
    'avg_income':       {'label': 'Avg Income',       'domain': 'finance',
                         'sql': 'AVG(f.amount)', 'format': 'currency'},
    'max_income':       {'label': 'Max Income',       'domain': 'finance',
                         'sql': 'MAX(f.amount)', 'format': 'currency'},
    'min_income':       {'label': 'Min Income',       'domain': 'finance',
                         'sql': 'MIN(f.amount)', 'format': 'currency'},
    # Schedule metrics
    'shift_count':      {'label': 'Shift Count',      'domain': 'schedule',
                         'sql': 'COUNT(*)', 'format': 'integer'},
    'absent_count':     {'label': 'Absent Count',     'domain': 'schedule',
                         'sql': 'SUM(CASE s.is_absent WHEN 1 THEN 1 ELSE 0 END)', 'format': 'integer'},
    'total_overtime':   {'label': 'Total Overtime',    'domain': 'schedule',
                         'sql': 'SUM(s.overtime)', 'format': 'integer'},
    'attendance_rate':  {'label': 'Attendance Rate',   'domain': 'schedule',
                         'sql': "ROUND((1.0 - CAST(SUM(CASE s.is_absent WHEN 1 THEN 1 ELSE 0 END) AS REAL) / NULLIF(COUNT(*), 0)) * 100, 1)",
                         'format': 'percent_val'},
}

# ---------------------------------------------------------------------------
# Base SQL for each domain
# ---------------------------------------------------------------------------

DONOR_BASE = (
    'FROM donors dn '
    'LEFT JOIN donations d ON dn.donor_id = d.donor_id'
)

PERSON_BASE = (
    'FROM persons p '
    'LEFT JOIN payments pay ON p.person_id = pay.person_id'
)

EVENT_BASE = (
    'FROM events e '
    'LEFT JOIN donors_events de ON e.event_id = de.event_id '
    'LEFT JOIN donors dn ON de.donor_id = dn.donor_id'
)

GIFT_BASE = (
    'FROM gifts g '
    'LEFT JOIN gift_batch gb ON g.gift_id = gb.gift_id '
    'LEFT JOIN gift_distribution gd ON gb.batch_id = gd.batch_id'
)

FINANCE_BASE = (
    "FROM ("
    "SELECT grant_name AS name, 'Grant' AS source_type, "
    "funding_org AS source, amount, received_date AS received "
    "FROM grants "
    "UNION ALL "
    "SELECT income_name, 'Other' AS source_type, "
    "source_name, amount, recevied_date "
    "FROM other_income"
    ") f"
)

SCHEDULE_BASE = (
    'FROM (SELECT *, "is_absent\t" AS is_absent FROM schedules) s '
    'LEFT JOIN persons p ON s.person_id = p.person_id '
    'LEFT JOIN events e ON s.event_id = e.event_id'
)

VALID_DOMAINS = ('donor', 'person', 'event', 'gift', 'finance', 'schedule')

DOMAIN_BASES = {
    'donor': DONOR_BASE,
    'person': PERSON_BASE,
    'event': EVENT_BASE,
    'gift': GIFT_BASE,
    'finance': FINANCE_BASE,
    'schedule': SCHEDULE_BASE,
}


def _detect_domain(filters, dimensions, metrics):
    """Determine query domain from selected fields."""
    all_keys = list(filters.keys()) + dimensions + metrics
    for dom in VALID_DOMAINS:
        if any(FILTER_DEFS.get(k, {}).get('domain') == dom or
               DIMENSION_DEFS.get(k, {}).get('domain') == dom or
               METRIC_DEFS.get(k, {}).get('domain') == dom
               for k in all_keys):
            return dom
    return 'donor'


def _build_query(domain, filters, dimensions, metrics):
    """Build a safe parameterised SQL query from whitelisted field names."""
    base = DOMAIN_BASES.get(domain, DONOR_BASE)
    params = []

    # SELECT clause
    select_parts = []
    for dim_key in dimensions:
        d = DIMENSION_DEFS.get(dim_key)
        if d and d['domain'] == domain:
            select_parts.append(f"{d['sql']} AS {d['alias']}")

    metric_keys_valid = []
    for m_key in metrics:
        m = METRIC_DEFS.get(m_key)
        if m and m['domain'] == domain:
            select_parts.append(f"{m['sql']} AS {m_key}")
            metric_keys_valid.append(m_key)

    if not select_parts:
        return None, None, []

    # WHERE clause
    where_parts = []
    for f_key, f_val in filters.items():
        fd = FILTER_DEFS.get(f_key)
        if not fd or fd['domain'] != domain:
            continue
        ftype = fd['type']
        sql_col = fd['sql']
        if ftype == 'range':
            lo = f_val.get('min')
            hi = f_val.get('max')
            if lo not in (None, ''):
                where_parts.append(f"{sql_col} >= ?")
                params.append(float(lo))
            if hi not in (None, ''):
                where_parts.append(f"{sql_col} <= ?")
                params.append(float(hi))
        elif ftype == 'daterange':
            lo = f_val.get('min')
            hi = f_val.get('max')
            if lo:
                where_parts.append(f"{sql_col} >= ?")
                params.append(lo)
            if hi:
                where_parts.append(f"{sql_col} <= ?")
                params.append(hi)
        elif ftype == 'enum':
            vals = f_val if isinstance(f_val, list) else [f_val]
            vals = [v for v in vals if v]
            if vals:
                placeholders = ','.join('?' * len(vals))
                where_parts.append(f"{sql_col} IN ({placeholders})")
                params.extend(vals)
        elif ftype == 'bool':
            if f_val in ('1', 1, True, 'true'):
                where_parts.append(f"{sql_col} = 1")
            elif f_val in ('0', 0, False, 'false'):
                where_parts.append(f"{sql_col} = 0")

    where_sql = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

    # GROUP BY clause
    group_parts = [DIMENSION_DEFS[k]['sql'] for k in dimensions
                   if k in DIMENSION_DEFS and DIMENSION_DEFS[k]['domain'] == domain]
    group_sql = ('GROUP BY ' + ', '.join(group_parts)) if group_parts else ''

    # ORDER BY — first dimension or first metric
    if group_parts:
        order_sql = f"ORDER BY {group_parts[0]}"
    else:
        order_sql = ''

    sql = f"SELECT {', '.join(select_parts)} {base} {where_sql} {group_sql} {order_sql}"
    return sql.strip(), params, metric_keys_valid


def _get_total(domain, filters):
    """Get total count for percent-of-total metrics."""
    totals = {
        'donor':    "SELECT COUNT(DISTINCT donor_id) AS total FROM donors",
        'person':   "SELECT COUNT(DISTINCT person_id) AS total FROM persons",
        'event':    "SELECT COUNT(DISTINCT event_id) AS total FROM events",
        'gift':     "SELECT COUNT(DISTINCT gift_id) AS total FROM gifts",
        'finance':  "SELECT COUNT(*) AS total FROM (SELECT 1 FROM grants UNION ALL SELECT 1 FROM other_income)",
        'schedule': "SELECT COUNT(*) AS total FROM schedules",
    }
    sql = totals.get(domain, totals['donor'])
    row = query_db(sql, one=True)
    return row['total'] if row else 1


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bi_bp.route('/bi')
@login_required
def bi_index():
    # Build options for dynamic filters
    filter_options = {}
    for key, fd in FILTER_DEFS.items():
        if 'options' in fd:
            filter_options[key] = fd['options']
        elif 'options_query' in fd:
            rows = query_db(fd['options_query'])
            filter_options[key] = [list(r)[0] for r in rows]

    return render_template('bi/index.html',
                           filter_defs=FILTER_DEFS,
                           dimension_defs=DIMENSION_DEFS,
                           metric_defs=METRIC_DEFS,
                           filter_options=filter_options)


@bi_bp.route('/api/bi/query', methods=['POST'])
@login_required
def bi_query():
    body = request.get_json(force=True)
    filters    = body.get('filters', {})
    dimensions = body.get('dimensions', [])
    metrics    = body.get('metrics', [])

    if not metrics:
        return jsonify(error='Select at least one metric'), 400

    # Accept explicit domain from frontend; fall back to auto-detection
    domain = body.get('domain', '')
    if domain not in VALID_DOMAINS:
        domain = _detect_domain(filters, dimensions, metrics)

    sql, params, valid_metrics = _build_query(domain, filters, dimensions, metrics)

    if not sql:
        return jsonify(error='No valid fields selected'), 400

    rows = query_db(sql, params)
    data = [dict(r) for r in rows]

    # Compute percent-of-total for percent metrics
    pct_metrics = [m for m in valid_metrics if METRIC_DEFS[m].get('format') == 'percent']
    if pct_metrics:
        total = _get_total(domain, filters)
        total = total or 1
        for row in data:
            for m in pct_metrics:
                raw = row.get(m) or 0
                row[m + '_pct'] = round(raw / total * 100, 2)
                row[m + '_total'] = total

    # Build column metadata for frontend rendering
    columns = []
    for dim_key in dimensions:
        d = DIMENSION_DEFS.get(dim_key)
        if d and d['domain'] == domain:
            columns.append({'key': d['alias'], 'label': d['label'], 'format': 'text'})
    for m_key in valid_metrics:
        m = METRIC_DEFS[m_key]
        if m.get('format') == 'percent':
            columns.append({'key': m_key + '_pct', 'label': m['label'], 'format': 'percent_val'})
        else:
            columns.append({'key': m_key, 'label': m['label'], 'format': m['format']})

    return jsonify(domain=domain, columns=columns, rows=data, total_rows=len(data))


@bi_bp.route('/api/bi/meta')
@login_required
def bi_meta():
    """Return filter options that require DB queries."""
    filter_options = {}
    for key, fd in FILTER_DEFS.items():
        if 'options' in fd:
            filter_options[key] = fd['options']
        elif 'options_query' in fd:
            rows = query_db(fd['options_query'])
            filter_options[key] = [list(r)[0] for r in rows]
    return jsonify(filter_options=filter_options,
                   filters=FILTER_DEFS,
                   dimensions=DIMENSION_DEFS,
                   metrics=METRIC_DEFS)
