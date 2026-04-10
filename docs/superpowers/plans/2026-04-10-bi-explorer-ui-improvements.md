# BI Explorer UI/UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand BI Explorer from 2 to 6 data domains, add chart type selection, collapsible query builder, table sorting, quick presets, URL state, and full bilingual i18n.

**Architecture:** Server-side `bi.py` adds 4 new domain definitions (Event, Gift, Finance, Schedule) with whitelist-validated SQL following the existing pattern. Client-side `index.html` gains UI features (chart toggle, collapse, sort, presets, URL hash). All new strings added to `i18n.js`. New CSS appended to `style.css`.

**Tech Stack:** Flask + Jinja2, SQLite3, Chart.js, Bootstrap 5 + Bootstrap Icons, vanilla JS, CSS custom properties

---

## File Map

| File | Role | Changes |
|------|------|---------|
| `blueprints/bi.py` (302 lines) | Backend — domain defs + query builder | Add ~150 lines: 4 domain bases, ~24 new filter/dim/metric defs, update `_detect_domain`, update `_build_query`, update `bi_query` to accept `domain` in POST body |
| `templates/bi/index.html` (791 lines) | Frontend — UI + JS logic | Add ~200 lines: 6-domain selector, preset row, chart type toggles, collapsible wrapper + summary bar, sortable headers, URL hash logic, update `collectParams`/`renderChart`/`renderResults` |
| `static/js/i18n.js` (780 lines) | Translations | Add ~55 new ZH keys before closing `};` at line 705 |
| `static/css/style.css` (1838 lines) | Styles | Append ~80 new lines at end of file |

---

### Task 1: Add 4 New Domain Definitions to Backend

**Files:**
- Modify: `blueprints/bi.py`

This is the foundation — all subsequent UI work depends on these definitions existing.

- [ ] **Step 1: Add Event domain definitions**

Insert after `FILTER_DEFS` `'payment_amount'` entry (line 36), before the closing `}`:

```python
    # Event filters
    'event_type':       {'label': 'Event Type',       'domain': 'event', 'type': 'enum',   'sql': 'e.event_type',
                         'options_query': "SELECT DISTINCT event_type FROM events WHERE event_type != '' ORDER BY event_type"},
    'event_status':     {'label': 'Event Status',     'domain': 'event', 'type': 'enum',   'sql': 'e.status',
                         'options': ['Planned', 'Ongoing', 'Completed', 'Cancelled']},
    'event_location':   {'label': 'Event Location',   'domain': 'event', 'type': 'enum',   'sql': 'e.location',
                         'options_query': "SELECT DISTINCT location FROM events WHERE location != '' ORDER BY location"},
    'event_date':       {'label': 'Event Date',       'domain': 'event', 'type': 'daterange', 'sql': 'e.start_date'},
    'target_amount':    {'label': 'Target Amount',    'domain': 'event', 'type': 'range',  'sql': 'e.target_amount'},
```

Insert after `DIMENSION_DEFS` `'payment_type'` entry (line 63), before the closing `}`:

```python
    'event_type':       {'label': 'Event Type',       'domain': 'event',  'sql': 'e.event_type',
                         'alias': 'event_type'},
    'event_status':     {'label': 'Event Status',     'domain': 'event',  'sql': 'e.status',
                         'alias': 'event_status'},
    'event_location':   {'label': 'Event Location',   'domain': 'event',  'sql': 'e.location',
                         'alias': 'event_location'},
    'event_year':       {'label': 'Event Year',       'domain': 'event',  'sql': "strftime('%Y', e.start_date)",
                         'alias': 'event_year'},
```

Insert after `METRIC_DEFS` `'avg_payment'` entry (line 93), before the closing `}`:

```python
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
```

- [ ] **Step 2: Add Gift domain definitions**

Insert after the Event filter entries in `FILTER_DEFS`:

```python
    # Gift filters
    'gift_type':        {'label': 'Gift Type',        'domain': 'gift', 'type': 'enum',   'sql': 'g.gift_type',
                         'options_query': "SELECT DISTINCT gift_type FROM gifts WHERE gift_type != '' ORDER BY gift_type"},
    'gift_active':      {'label': 'Gift Active',      'domain': 'gift', 'type': 'bool',   'sql': 'g.is_active'},
    'unit_cost':        {'label': 'Unit Cost',        'domain': 'gift', 'type': 'range',  'sql': 'g.unit_cost'},
    'is_free':          {'label': 'Free Distribution','domain': 'gift', 'type': 'bool',   'sql': 'gd.is_free'},
```

Insert after Event dimension entries in `DIMENSION_DEFS`:

```python
    'gift_type':        {'label': 'Gift Type',        'domain': 'gift',  'sql': 'g.gift_type',
                         'alias': 'gift_type'},
    'gift_active_dim':  {'label': 'Gift Active',      'domain': 'gift',
                         'sql': "CASE g.is_active WHEN 1 THEN 'Active' ELSE 'Inactive' END",
                         'alias': 'gift_active'},
    'is_free_dim':      {'label': 'Distribution Type','domain': 'gift',
                         'sql': "CASE gd.is_free WHEN 1 THEN 'Free' ELSE 'Donor Gift' END",
                         'alias': 'distribution_type'},
```

Insert after Event metric entries in `METRIC_DEFS`:

```python
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
```

- [ ] **Step 3: Add Finance domain definitions**

Insert after Gift filter entries in `FILTER_DEFS`:

```python
    # Finance filters
    'source_type':      {'label': 'Source Type',      'domain': 'finance', 'type': 'enum',  'sql': 'f.source_type',
                         'options': ['Grant', 'Other']},
    'finance_amount':   {'label': 'Amount',           'domain': 'finance', 'type': 'range', 'sql': 'f.amount'},
    'finance_date':     {'label': 'Received Date',    'domain': 'finance', 'type': 'daterange', 'sql': 'f.received'},
```

Insert after Gift dimension entries in `DIMENSION_DEFS`:

```python
    'finance_source_type': {'label': 'Source Type',   'domain': 'finance', 'sql': 'f.source_type',
                            'alias': 'source_type'},
    'finance_source':      {'label': 'Source',        'domain': 'finance', 'sql': 'f.source',
                            'alias': 'source'},
    'finance_year':        {'label': 'Year',          'domain': 'finance',
                            'sql': "strftime('%Y', f.received)",
                            'alias': 'finance_year'},
```

Insert after Gift metric entries in `METRIC_DEFS`:

```python
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
```

- [ ] **Step 4: Add Schedule domain definitions**

Insert after Finance filter entries in `FILTER_DEFS`:

```python
    # Schedule filters
    'shift_date':       {'label': 'Shift Date',       'domain': 'schedule', 'type': 'daterange', 'sql': 's.shift_date'},
    'schedule_status':  {'label': 'Status',           'domain': 'schedule', 'type': 'enum',  'sql': 's.status',
                         'options': ['Scheduled', 'In Progress', 'Completed', 'Absent']},
    'is_absent_filter': {'label': 'Absent',           'domain': 'schedule', 'type': 'bool',  'sql': 's.is_absent'},
    'overtime':         {'label': 'Overtime (hrs)',    'domain': 'schedule', 'type': 'range', 'sql': 's.overtime'},
```

Insert after Finance dimension entries in `DIMENSION_DEFS`:

```python
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
```

Insert after Finance metric entries in `METRIC_DEFS`:

```python
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
```

- [ ] **Step 5: Add base SQL constants and update query builder**

Insert after `PERSON_BASE` (line 108):

```python
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
```

Replace the `_detect_domain` function with:

```python
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
```

Replace the first line of `_build_query`:

```python
    base = DOMAIN_BASES.get(domain, DONOR_BASE)
```

Replace the old line:
```python
    base = DONOR_BASE if domain == 'donor' else PERSON_BASE
```

- [ ] **Step 6: Update bi_query route to accept domain from POST body**

Replace the `bi_query` route function with:

```python
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
```

Update `_get_total` to handle new domains:

```python
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
```

- [ ] **Step 7: Verify backend by starting the server**

Run: `cd C:\Users\XF\Desktop\elder_care_gui && python app.py`

Open browser to `http://127.0.0.1:5000/bi`, login as admin/admin123. Verify the page loads without Python errors. The UI still shows only 2 domain buttons (frontend not updated yet), but no server errors should appear.

- [ ] **Step 8: Commit**

```bash
git add blueprints/bi.py
git commit -m "feat(bi): add Event, Gift, Finance, Schedule domain definitions

Expand BI Explorer backend from 2 to 6 data domains with whitelist-validated
filters, dimensions, and metrics. Accept explicit domain in POST body."
```

---

### Task 2: Update Frontend Domain Selector to 6 Domains

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Replace domain selector card**

Replace the entire domain selector card (lines 174-184 of `index.html`):

```html
<!-- Domain Selector -->
<div class="card mb-3" style="border:1px solid var(--border-warm);background:var(--bg-card);box-shadow:var(--shadow-sm);">
  <div class="card-body py-3">
    <label class="form-label fw-semibold mb-2" style="font-size:.85rem;color:var(--text-primary);" data-i18n="Data Domain">Data Domain</label>
    <div class="btn-group w-100" role="group">
      <input type="radio" class="btn-check" name="biDomain" id="domainDonor" value="donor" checked>
      <label class="btn bi-domain-btn" for="domainDonor"><i class="bi bi-people-fill me-1"></i><span data-i18n="Donors">Donors</span></label>
      <input type="radio" class="btn-check" name="biDomain" id="domainPerson" value="person">
      <label class="btn bi-domain-btn" for="domainPerson"><i class="bi bi-person-badge-fill me-1"></i><span data-i18n="Personnel">Personnel</span></label>
    </div>
  </div>
</div>
```

With this new 6-button version (2 rows of 3):

```html
<!-- Domain Selector -->
<div class="card mb-3" style="border:1px solid var(--border-warm);background:var(--bg-card);box-shadow:var(--shadow-sm);">
  <div class="card-body py-3">
    <label class="form-label fw-semibold mb-2" style="font-size:.85rem;color:var(--text-primary);" data-i18n="Data Domain">Data Domain</label>
    <div class="row g-2">
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainDonor" value="donor" checked>
        <label class="btn bi-domain-btn w-100" for="domainDonor"><i class="bi bi-people-fill me-1"></i><span data-i18n="Donors">Donors</span></label>
      </div>
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainPerson" value="person">
        <label class="btn bi-domain-btn w-100" for="domainPerson"><i class="bi bi-person-badge-fill me-1"></i><span data-i18n="Personnel">Personnel</span></label>
      </div>
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainEvent" value="event">
        <label class="btn bi-domain-btn w-100" for="domainEvent"><i class="bi bi-calendar-event-fill me-1"></i><span data-i18n="Events">Events</span></label>
      </div>
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainGift" value="gift">
        <label class="btn bi-domain-btn w-100" for="domainGift"><i class="bi bi-gift-fill me-1"></i><span data-i18n="Gifts">Gifts</span></label>
      </div>
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainFinance" value="finance">
        <label class="btn bi-domain-btn w-100" for="domainFinance"><i class="bi bi-cash-stack me-1"></i><span data-i18n="Finance">Finance</span></label>
      </div>
      <div class="col-4">
        <input type="radio" class="btn-check" name="biDomain" id="domainSchedule" value="schedule">
        <label class="btn bi-domain-btn w-100" for="domainSchedule"><i class="bi bi-clock-fill me-1"></i><span data-i18n="Schedules">Schedules</span></label>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Update collectParams to include domain**

In the `<script>` block, find the `collectParams()` function and change the return statement from:

```javascript
    return { filters, dimensions, metrics };
```

To:

```javascript
    return { domain: currentDomain, filters, dimensions, metrics };
```

- [ ] **Step 3: Update page subtitle**

Replace the subtitle text:

```html
<p class="text-muted mb-0" style="font-size:.85rem;" data-i18n="Build custom queries to analyze people data across donors and personnel">Build custom queries to analyze people data across donors and personnel</p>
```

With:

```html
<p class="text-muted mb-0" style="font-size:.85rem;" data-i18n="Build custom queries to analyze data across all foundation modules">Build custom queries to analyze data across all foundation modules</p>
```

- [ ] **Step 4: Verify — open browser, switch between all 6 domains, confirm filters/dims/metrics update per domain**

- [ ] **Step 5: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): expand domain selector to 6 domains (2x3 grid)

Add Events, Gifts, Finance, Schedules domain buttons. Include domain
in API request body. Update page subtitle."
```

---

### Task 3: Add Chart Type Selector

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Add chart type toggle buttons to chart card header**

Replace the chart card header (line 295-297 of `index.html`):

```html
<div class="card-header" style="background:var(--bg-card);border-bottom:2px solid var(--border-warm);">
    <i class="bi bi-bar-chart-fill me-2" style="color:var(--terracotta);"></i><span data-i18n="Chart">Chart</span>
  </div>
```

With:

```html
  <div class="card-header d-flex align-items-center justify-content-between" style="background:var(--bg-card);border-bottom:2px solid var(--border-warm);">
    <span><i class="bi bi-bar-chart-fill me-2" style="color:var(--terracotta);"></i><span data-i18n="Chart">Chart</span></span>
    <div class="btn-group btn-group-sm" id="chartTypeGroup">
      <button class="btn bi-chart-type-btn active" data-chart="bar" title="Bar Chart" data-i18n-title="Bar Chart"><i class="bi bi-bar-chart-fill"></i></button>
      <button class="btn bi-chart-type-btn" data-chart="horizontalBar" title="Horizontal Bar" data-i18n-title="Horizontal Bar"><i class="bi bi-bar-chart-steps"></i></button>
      <button class="btn bi-chart-type-btn" data-chart="doughnut" title="Doughnut Chart" data-i18n-title="Doughnut Chart"><i class="bi bi-pie-chart-fill"></i></button>
      <button class="btn bi-chart-type-btn" data-chart="line" title="Line Chart" data-i18n-title="Line Chart"><i class="bi bi-graph-up"></i></button>
    </div>
  </div>
```

- [ ] **Step 2: Add chart type state and smart default logic**

In the `<script>` block, add after `let biChart = null;` (line 316):

```javascript
  let chartType = 'bar';
  let lastQueryData = null; // Store last query result for chart re-render

  function suggestChartType(rows, dimCols, metCols) {
    if (dimCols.length === 0) return 'bar';
    const dimAlias = dimCols[0].key || '';
    if (dimAlias.includes('year') || dimAlias.includes('month')) return 'line';
    if (metCols.length === 1 && rows.length <= 8) return 'doughnut';
    const avgLen = rows.reduce((s, r) => s + String(r[dimCols[0].key] || '').length, 0) / (rows.length || 1);
    if (avgLen > 12) return 'horizontalBar';
    return 'bar';
  }
```

- [ ] **Step 3: Replace the renderChart function**

Replace the entire `renderChart` function with:

```javascript
  function renderChart(rows, dimCol, metCols, type) {
    const wrap = document.getElementById('biChartWrap');
    wrap.style.display = '';
    const ctx = document.getElementById('biChart').getContext('2d');
    if (biChart) biChart.destroy();

    // Store for re-render on chart type change
    lastQueryData = { rows, dimCol, metCols };

    chartType = type || suggestChartType(rows, [dimCol], metCols);
    // Update active button
    document.querySelectorAll('.bi-chart-type-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.chart === chartType);
    });

    const labels = rows.map(r => I18n.t(String(r[dimCol.key] || '—')));
    const palette = ['#5a8a6a', '#c07a56', '#c8a45c', '#8a6dab', '#5a8a8a', '#a06a46', '#6a8a5a'];
    const filteredMets = metCols.filter(c => c.format !== 'percent_val');

    if (chartType === 'doughnut') {
      // Doughnut: use first metric only
      const col = filteredMets[0];
      if (!col) return;
      biChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data: rows.map(r => r[col.key] || 0),
            backgroundColor: palette.slice(0, rows.length).map(c => c + 'cc'),
            borderColor: palette.slice(0, rows.length),
            borderWidth: 1,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { font: { family: 'Outfit', size: 12 } } },
            tooltip: {
              backgroundColor: '#1a1a2e', titleFont: { family: 'Outfit' }, bodyFont: { family: 'Outfit' },
              callbacks: {
                label: function(ctx) { return ctx.label + ': ' + formatValue(ctx.raw, col.format); }
              }
            }
          }
        }
      });
    } else {
      // Bar, Horizontal Bar, Line
      const isHorizontal = chartType === 'horizontalBar';
      const cType = isHorizontal ? 'bar' : (chartType === 'line' ? 'line' : 'bar');
      const datasets = filteredMets.map((col, i) => ({
        label: I18n.t(col.label),
        data: rows.map(r => r[col.key] || 0),
        backgroundColor: palette[i % palette.length] + 'cc',
        borderColor: palette[i % palette.length],
        borderWidth: chartType === 'line' ? 2 : 1,
        borderRadius: chartType === 'line' ? 0 : 4,
        tension: chartType === 'line' ? 0.3 : 0,
        fill: chartType === 'line' ? false : undefined,
        pointRadius: chartType === 'line' ? 4 : 0,
        pointHoverRadius: chartType === 'line' ? 6 : 0,
      }));

      biChart = new Chart(ctx, {
        type: cType,
        data: { labels, datasets },
        options: {
          indexAxis: isHorizontal ? 'y' : 'x',
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { labels: { font: { family: 'Outfit', size: 12 } } },
            tooltip: {
              backgroundColor: '#1a1a2e', titleFont: { family: 'Outfit' }, bodyFont: { family: 'Outfit' },
              callbacks: {
                label: function(ctx) {
                  const col = filteredMets[ctx.datasetIndex];
                  if (!col) return ctx.formattedValue;
                  return ctx.dataset.label + ': ' + formatValue(ctx.raw, col.format);
                }
              }
            }
          },
          scales: {
            x: { ticks: { font: { family: 'Outfit', size: 11 } }, beginAtZero: !isHorizontal },
            y: { ticks: { font: { family: 'Outfit', size: 11 } }, beginAtZero: isHorizontal || chartType !== 'line' }
          }
        }
      });
    }
  }
```

- [ ] **Step 4: Add chart type button click handlers**

Add after the `closeAllDropdowns` function:

```javascript
  // Chart type toggle
  document.getElementById('chartTypeGroup').addEventListener('click', function(e) {
    const btn = e.target.closest('.bi-chart-type-btn');
    if (!btn || !lastQueryData) return;
    const newType = btn.dataset.chart;
    renderChart(lastQueryData.rows, lastQueryData.dimCol, lastQueryData.metCols, newType);
  });
```

- [ ] **Step 5: Update the call site in renderResults**

Find this line in `renderResults`:

```javascript
      renderChart(rows, dimCols[0], metCols);
```

Replace with:

```javascript
      renderChart(rows, dimCols[0], metCols, null);
```

(Passing `null` triggers the smart default selection.)

- [ ] **Step 6: Verify — run a query with dimensions, confirm chart appears, click all 4 chart type buttons**

- [ ] **Step 7: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): add chart type selector (bar/horizontal/doughnut/line)

Smart default picks line for temporal dims, doughnut for single-metric
small results. User can override via toggle buttons in chart header."
```

---

### Task 4: Add Collapsible Query Builder

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Wrap domain selector and three-panel row in collapsible container**

Wrap the domain selector card and the `<div class="row g-3 mb-3">` (three-panel builder) in a new div. Add a query summary bar right after it.

Insert before the domain selector card:

```html
<!-- Query Summary Bar (shown when collapsed) -->
<div id="biQuerySummary" class="bi-query-summary" style="display:none;">
  <div class="d-flex align-items-center flex-wrap gap-2">
    <span class="bi-ms-tag" id="summaryDomain" style="background:linear-gradient(135deg,#3d6b4e,#5a8a6a);"></span>
    <span id="summaryDims"></span>
    <span id="summaryMets"></span>
    <span id="summaryFilters" class="badge rounded-pill" style="background:var(--text-muted);color:#fff;font-size:.7rem;"></span>
    <button class="btn btn-sm btn-outline-secondary ms-auto" id="btnModifyQuery" style="font-weight:600;font-size:.8rem;">
      <i class="bi bi-pencil-square me-1"></i><span data-i18n="Modify Query">Modify Query</span>
    </button>
  </div>
</div>

<div id="biBuilderWrap" class="bi-builder-wrap">
```

Insert after the closing `</div>` of the three-panel row (after `<!-- Metrics Panel -->` section ends):

```html
</div><!-- /biBuilderWrap -->
```

- [ ] **Step 2: Add collapse/expand logic**

Add after the chart type toggle handler:

```javascript
  let builderCollapsed = false;

  function collapseBuilder() {
    const wrap = document.getElementById('biBuilderWrap');
    const summary = document.getElementById('biQuerySummary');
    wrap.classList.add('collapsed');
    builderCollapsed = true;

    // Populate summary
    const domainLabel = document.querySelector('input[name="biDomain"]:checked + label span');
    document.getElementById('summaryDomain').textContent = domainLabel ? domainLabel.textContent : currentDomain;

    let dimHtml = '';
    selectedDims.forEach(k => {
      const dd = DIMENSION_DEFS[k];
      if (dd && dd.domain === currentDomain) dimHtml += '<span class="bi-ms-tag dim-tag">' + I18n.t(dd.label) + '</span> ';
    });
    document.getElementById('summaryDims').innerHTML = dimHtml;

    let metHtml = '';
    selectedMets.forEach(k => {
      const md = METRIC_DEFS[k];
      if (md && md.domain === currentDomain) metHtml += '<span class="bi-ms-tag met-tag">' + I18n.t(md.label) + '</span> ';
    });
    document.getElementById('summaryMets').innerHTML = metHtml;

    const filterCount = activeFilterKeys.filter(k => FILTER_DEFS[k] && FILTER_DEFS[k].domain === currentDomain).length;
    const filterBadge = document.getElementById('summaryFilters');
    if (filterCount > 0) {
      filterBadge.textContent = filterCount + ' ' + I18n.t(filterCount === 1 ? 'filter' : 'filters');
      filterBadge.style.display = '';
    } else {
      filterBadge.style.display = 'none';
    }

    summary.style.display = '';
  }

  function expandBuilder() {
    const wrap = document.getElementById('biBuilderWrap');
    const summary = document.getElementById('biQuerySummary');
    wrap.classList.remove('collapsed');
    summary.style.display = 'none';
    builderCollapsed = false;
  }

  document.getElementById('btnModifyQuery').addEventListener('click', expandBuilder);
```

- [ ] **Step 3: Call collapseBuilder after successful query**

In the `runQuery` function, after `renderResults(data);`, add:

```javascript
      collapseBuilder();
```

Also, in the Clear All handler, add `expandBuilder();` call:

```javascript
  document.getElementById('btnClear').addEventListener('click', function() {
    activeFilterKeys = [];
    renderAll();
    expandBuilder();
  });
```

- [ ] **Step 4: Verify — run a query, confirm panels collapse, click "Modify Query" to expand**

- [ ] **Step 5: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): collapsible query builder with summary bar

After query runs, panels collapse to show domain/dims/metrics/filter
tags. Modify Query button re-expands. Saves ~400px vertical space."
```

---

### Task 5: Add Table Column Sorting

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Add sort state and sort logic**

Add after the `collapseBuilder`/`expandBuilder` code:

```javascript
  let sortCol = null;
  let sortDir = null; // 'asc', 'desc', or null
  let lastColumns = [];
  let lastRows = [];

  function sortAndRender() {
    let rows = [...lastRows];
    if (sortCol !== null && sortDir !== null) {
      const col = lastColumns[sortCol];
      const isNum = col && col.format !== 'text';
      rows.sort((a, b) => {
        let va = a[col.key], vb = b[col.key];
        if (va === null || va === undefined) va = isNum ? -Infinity : '';
        if (vb === null || vb === undefined) vb = isNum ? -Infinity : '';
        if (isNum) {
          va = Number(va); vb = Number(vb);
          return sortDir === 'asc' ? va - vb : vb - va;
        }
        va = String(va); vb = String(vb);
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      });
    }
    renderTableBody(rows, lastColumns);
    renderSortIndicators();
  }

  function renderTableBody(rows, columns) {
    const tbody = document.getElementById('biTableBody');
    tbody.innerHTML = '';
    rows.forEach(row => {
      const tr = document.createElement('tr');
      columns.forEach(col => {
        const td = document.createElement('td');
        td.style.fontSize = '.85rem';
        td.textContent = formatValue(row[col.key], col.format);
        if (col.format !== 'text') td.style.textAlign = 'right';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  function renderSortIndicators() {
    document.querySelectorAll('#biTableHead th').forEach((th, i) => {
      let icon = th.querySelector('.bi-sort-icon');
      if (!icon) {
        icon = document.createElement('i');
        icon.className = 'bi-sort-icon ms-1';
        icon.style.cssText = 'font-size:.7rem;opacity:.4;';
        th.appendChild(icon);
      }
      if (i === sortCol && sortDir === 'asc') {
        icon.className = 'bi bi-chevron-up bi-sort-icon ms-1';
        icon.style.opacity = '1';
      } else if (i === sortCol && sortDir === 'desc') {
        icon.className = 'bi bi-chevron-down bi-sort-icon ms-1';
        icon.style.opacity = '1';
      } else {
        icon.className = 'bi bi-chevron-expand bi-sort-icon ms-1';
        icon.style.opacity = '.4';
      }
    });
  }
```

- [ ] **Step 2: Update renderResults to store data and attach sort handlers**

In the `renderResults` function, right before the table rendering code (`columns.forEach(col => {` for the `<thead>`), add:

```javascript
    // Store for sorting
    lastColumns = columns;
    lastRows = [...rows];
    sortCol = null;
    sortDir = null;
```

Replace the thead column rendering loop:

```javascript
    columns.forEach(col => {
      const th = document.createElement('th');
      th.className = 'table-header';
      th.textContent = I18n.t(col.label);
      th.style.cssText = 'font-size:.8rem;white-space:nowrap;';
      thead.appendChild(th);
    });
```

With:

```javascript
    columns.forEach((col, colIdx) => {
      const th = document.createElement('th');
      th.className = 'table-header bi-sortable';
      th.style.cssText = 'font-size:.8rem;white-space:nowrap;cursor:pointer;user-select:none;';
      th.textContent = I18n.t(col.label);
      th.addEventListener('click', function() {
        if (sortCol === colIdx) {
          sortDir = sortDir === 'asc' ? 'desc' : (sortDir === 'desc' ? null : 'asc');
          if (sortDir === null) sortCol = null;
        } else {
          sortCol = colIdx;
          sortDir = 'asc';
        }
        sortAndRender();
      });
      thead.appendChild(th);
    });
    renderSortIndicators();
```

- [ ] **Step 3: Verify — run a query, click table headers, confirm sort cycles asc → desc → unsorted**

- [ ] **Step 4: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): add client-side table column sorting

Click headers to cycle asc/desc/unsorted. Numeric columns sort
numerically, text columns sort locale-aware alphabetically."
```

---

### Task 6: Add Quick Presets

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Add presets constant and HTML row**

In the `<script>` block, add after `let currentDomain = 'donor';`:

```javascript
  const PRESETS = [
    { label: 'Donations by Type',  domain: 'donor',    dims: ['donation_type'],         mets: ['donor_count', 'total_donation'] },
    { label: 'Donors by Location', domain: 'donor',    dims: ['donor_location'],        mets: ['donor_count', 'total_donation'] },
    { label: 'Staff Payments',     domain: 'person',   dims: ['person_role'],           mets: ['person_count', 'total_payment'] },
    { label: 'Events Overview',    domain: 'event',    dims: ['event_type'],            mets: ['event_count', 'total_actual'] },
    { label: 'Gift Inventory',     domain: 'gift',     dims: ['gift_type'],             mets: ['gift_count', 'total_stock', 'total_inventory_value'] },
    { label: 'Income Sources',     domain: 'finance',  dims: ['finance_source_type'],   mets: ['income_count', 'total_income'] },
  ];
  let activePreset = -1;
```

Insert the preset row HTML before the domain selector card (before `<div id="biBuilderWrap">`):

```html
<!-- Quick Presets -->
<div class="bi-preset-row mb-3" style="overflow-x:auto;white-space:nowrap;padding:2px 0;">
  <span class="me-2" style="font-size:.8rem;font-weight:600;color:var(--text-secondary);" data-i18n="Presets">Presets</span>
  <span id="presetContainer"></span>
</div>
```

- [ ] **Step 2: Add preset rendering and click logic**

Add after the PRESETS constant:

```javascript
  function renderPresets() {
    const container = document.getElementById('presetContainer');
    container.innerHTML = '';
    PRESETS.forEach((p, i) => {
      const btn = document.createElement('button');
      btn.className = 'btn btn-sm bi-preset-pill' + (activePreset === i ? ' active' : '');
      btn.textContent = I18n.t(p.label);
      btn.addEventListener('click', function() {
        if (activePreset === i) {
          activePreset = -1;
          renderPresets();
          return;
        }
        activePreset = i;
        // Set domain
        currentDomain = p.domain;
        const radio = document.getElementById('domainDonor').parentElement.querySelector('input[value="' + p.domain + '"]');
        if (radio) radio.checked = true;
        // Set dims and metrics
        activeFilterKeys = [];
        selectedDims = [...p.dims];
        selectedMets = [...p.mets];
        renderFilterDropdown();
        renderActiveFilters();
        renderDimTrigger();
        renderDimDropdown();
        renderMetTrigger();
        renderMetDropdown();
        renderPresets();
        // Auto-run
        runQuery();
      });
      container.appendChild(btn);
    });
  }
```

- [ ] **Step 3: Call renderPresets on init and domain change**

Add `renderPresets();` to the end of `renderAll()` function, right before the closing `}`:

```javascript
  function renderAll() {
    renderFilterDropdown();
    renderActiveFilters();
    renderDimensions();
    renderMetrics();
    hideResults();
    activePreset = -1;
    renderPresets();
  }
```

- [ ] **Step 4: Verify — click each of the 6 presets, confirm domain switches, query runs, results appear**

- [ ] **Step 5: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): add 6 quick preset query pills

One-click presets for common analyses across all 6 domains.
Clicking a preset sets domain, dims, metrics and auto-runs the query."
```

---

### Task 7: Add URL Query State

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Add URL hash encoding after successful query**

Add after the `collapseBuilder()` call in `runQuery`:

```javascript
      // Encode query state to URL hash
      try {
        const state = { domain: currentDomain, dimensions: [...selectedDims], metrics: [...selectedMets], filters: collectParams().filters };
        const encoded = btoa(JSON.stringify(state));
        history.replaceState(null, '', '#q=' + encoded);
      } catch(e) { /* ignore encoding errors */ }
```

- [ ] **Step 2: Add URL hash decoding on page load**

Add at the very end of the IIFE, before the closing `})();`:

```javascript
  // Restore state from URL hash
  (function restoreFromHash() {
    try {
      const hash = location.hash;
      if (!hash.startsWith('#q=')) return;
      const state = JSON.parse(atob(hash.slice(3)));
      if (!state.domain || !PRESETS) return; // sanity check

      // Restore domain
      currentDomain = state.domain;
      const radio = document.querySelector('input[name="biDomain"][value="' + state.domain + '"]');
      if (radio) radio.checked = true;

      // Rebuild panels for this domain
      renderFilterDropdown();
      renderActiveFilters();

      // Restore dimensions
      if (Array.isArray(state.dimensions)) {
        selectedDims = state.dimensions.filter(k => DIMENSION_DEFS[k] && DIMENSION_DEFS[k].domain === currentDomain);
        renderDimTrigger();
        renderDimDropdown();
      }

      // Restore metrics
      if (Array.isArray(state.metrics)) {
        selectedMets = state.metrics.filter(k => METRIC_DEFS[k] && METRIC_DEFS[k].domain === currentDomain);
        renderMetTrigger();
        renderMetDropdown();
      }

      // Restore filters — set values into filter inputs after they're rendered
      if (state.filters && typeof state.filters === 'object') {
        Object.keys(state.filters).forEach(k => {
          if (FILTER_DEFS[k] && FILTER_DEFS[k].domain === currentDomain && !activeFilterKeys.includes(k)) {
            activeFilterKeys.push(k);
          }
        });
        renderFilterDropdown();
        renderActiveFilters();
        // Set filter values after DOM update
        setTimeout(() => {
          Object.entries(state.filters).forEach(([k, v]) => {
            const fd = FILTER_DEFS[k];
            if (!fd) return;
            if (fd.type === 'range' || fd.type === 'daterange') {
              if (v.min) { const inp = document.querySelector('.bi-filter-input[data-key="'+k+'"][data-bound="min"]'); if(inp) inp.value = v.min; }
              if (v.max) { const inp = document.querySelector('.bi-filter-input[data-key="'+k+'"][data-bound="max"]'); if(inp) inp.value = v.max; }
            } else if (fd.type === 'enum' && Array.isArray(v)) {
              v.forEach(val => { const cb = document.querySelector('.bi-filter-enum[data-key="'+k+'"][value="'+val+'"]'); if(cb) cb.checked = true; });
            } else if (fd.type === 'bool' && v) {
              const cb = document.querySelector('.bi-filter-bool[data-key="'+k+'"]'); if(cb) cb.checked = true;
            }
          });
          runQuery();
        }, 50);
      } else {
        runQuery();
      }
    } catch(e) { /* ignore invalid hash */ }
  })();
```

- [ ] **Step 3: Clear hash on Clear All**

In the Clear All handler, add:

```javascript
    history.replaceState(null, '', location.pathname);
```

- [ ] **Step 4: Verify — run a query, check URL hash updates, copy URL, paste in new tab, confirm query restores**

- [ ] **Step 5: Commit**

```bash
git add templates/bi/index.html
git commit -m "feat(bi): persist query state in URL hash

Query encoded as base64 JSON in #q= hash. Supports bookmarking and
sharing. Decoded on page load to restore full query state."
```

---

### Task 8: Add i18n Translations

**Files:**
- Modify: `static/js/i18n.js`

- [ ] **Step 1: Add all new translation keys**

Insert before the closing `};` of the `ZH` dictionary (line 705 of `i18n.js`), add:

```javascript
    // ── BI Explorer — New domains & UI ──
    'Build custom queries to analyze data across all foundation modules': '构建自定义查询，分析基金会所有模块的数据',
    'Events': '活动',
    'Gifts': '礼品',
    'Finance': '财务',
    'Schedules': '排班',
    // Event domain labels
    'Event Type': '活动类型',
    'Event Status': '活动状态',
    'Event Location': '活动地点',
    'Event Date': '活动日期',
    'Target Amount': '目标金额',
    'Event Year': '活动年份',
    'Event Count': '活动数量',
    'Participant Count': '参与人数',
    'Total Target Amount': '目标总金额',
    'Total Actual Amount': '实际总金额',
    'Avg Target Amount': '平均目标金额',
    'Achievement Rate': '达成率',
    // Gift domain labels
    'Gift Type': '礼品类型',
    'Gift Active': '礼品状态',
    'Free Distribution': '免费分发',
    'Unit Cost': '单位成本',
    'Distribution Type': '分发类型',
    'Gift Count': '礼品数量',
    'Total Stock': '总库存',
    'Total Distributed': '已分发总量',
    'Inventory Value': '库存价值',
    'Avg Unit Cost': '平均单位成本',
    'Active': '活跃',
    'Inactive': '停用',
    'Free': '免费',
    'Donor Gift': '捐赠礼品',
    // Finance domain labels
    'Source Type': '来源类型',
    'Amount': '金额',
    'Received Date': '到账日期',
    'Source': '来源',
    'Year': '年份',
    'Income Count': '收入笔数',
    'Total Income': '总收入',
    'Avg Income': '平均收入',
    'Max Income': '最大收入',
    'Min Income': '最小收入',
    'Grant': '拨款',
    'Other': '其他',
    // Schedule domain labels
    'Shift Date': '排班日期',
    'Absent': '缺勤',
    'Overtime (hrs)': '加班（小时）',
    'Schedule Status': '排班状态',
    'Attendance': '出勤情况',
    'Shift Month': '排班月份',
    'Shift Count': '班次数量',
    'Absent Count': '缺勤次数',
    'Total Overtime': '加班总时数',
    'Attendance Rate': '出勤率',
    'Present': '出勤',
    // UI strings
    'Modify Query': '修改查询',
    'Presets': '预设查询',
    'Bar Chart': '柱状图',
    'Horizontal Bar': '条形图',
    'Doughnut Chart': '饼图',
    'Line Chart': '折线图',
    'Sort ascending': '升序排列',
    'Sort descending': '降序排列',
    'filter': '个筛选',
    'filters': '个筛选',
    // Preset labels
    'Donations by Type': '按类型统计捐款',
    'Donors by Location': '按地区统计捐赠者',
    'Staff Payments': '员工薪酬统计',
    'Events Overview': '活动概览',
    'Gift Inventory': '礼品库存',
    'Income Sources': '收入来源',
```

- [ ] **Step 2: Verify — switch to Chinese, navigate to BI Explorer, confirm all new labels show Chinese**

- [ ] **Step 3: Commit**

```bash
git add static/js/i18n.js
git commit -m "feat(i18n): add ~70 ZH translations for BI Explorer expansion

Covers all 4 new domains (Event/Gift/Finance/Schedule), chart type
labels, presets, and UI strings."
```

---

### Task 9: Add CSS Styles

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Append BI Explorer enhancement styles to end of file**

Append after line 1838 (end of `.login-lang-toggle`):

```css

/* ── BI Explorer Enhancements ─────────────────── */
.bi-builder-wrap {
  max-height: 2000px;
  overflow: visible;
  opacity: 1;
  transition: max-height .35s var(--ease), opacity .25s var(--ease);
}
.bi-builder-wrap.collapsed {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
}

.bi-query-summary {
  background: var(--bg-card);
  border: 1.5px solid var(--border-warm);
  border-radius: 10px;
  padding: .6rem 1rem;
  margin-bottom: .75rem;
  box-shadow: var(--shadow-sm);
}

.bi-chart-type-btn {
  border: 1.5px solid var(--border-warm) !important;
  background: transparent;
  color: var(--text-muted);
  padding: .25rem .5rem;
  font-size: .85rem;
  transition: all .2s var(--ease);
}
.bi-chart-type-btn:hover {
  border-color: var(--accent) !important;
  color: var(--accent);
  background: var(--accent-soft);
}
.bi-chart-type-btn.active {
  background: linear-gradient(135deg, #3d6b4e, #5a8a6a) !important;
  border-color: #3d6b4e !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(61,107,78,.25);
}

.bi-sortable {
  cursor: pointer;
  user-select: none;
  transition: background .15s;
}
.bi-sortable:hover {
  background: rgba(90,138,106,.06);
}
.bi-sort-icon {
  font-size: .7rem;
  transition: opacity .15s;
}

.bi-preset-pill {
  border: 1.5px solid var(--accent);
  background: transparent;
  color: var(--accent);
  font-weight: 600;
  font-size: .78rem;
  padding: .3rem .75rem;
  border-radius: 20px;
  margin-right: .4rem;
  white-space: nowrap;
  transition: all .2s var(--ease);
}
.bi-preset-pill:hover {
  background: var(--accent-soft);
  border-color: var(--accent-hover);
  color: var(--accent-hover);
}
.bi-preset-pill.active {
  background: linear-gradient(135deg, #3d6b4e, #5a8a6a);
  border-color: #3d6b4e;
  color: #fff;
  box-shadow: 0 2px 8px rgba(61,107,78,.25);
}

@media (max-width: 767.98px) {
  .bi-preset-row { padding-bottom: .5rem; }
  .bi-domain-btn { font-size: .78rem; padding: .35rem .5rem; }
}
```

- [ ] **Step 2: Verify — check all new UI elements are properly styled**

- [ ] **Step 3: Commit**

```bash
git add static/css/style.css
git commit -m "style(bi): add CSS for chart toggles, collapsible builder, sort, presets

~75 lines: chart type button styles, collapsible builder transition,
sortable header hover, preset pill badges, responsive adjustments."
```

---

### Task 10: Final Integration Verification

- [ ] **Step 1: Full browser test**

Start the server and test all 6 domains:

1. Login as admin/admin123
2. Navigate to BI Explorer
3. Click each of the 6 domain buttons — verify filters/dims/metrics update
4. Click each of the 6 preset pills — verify auto-query runs
5. Run a custom query with dims + metrics — verify:
   - Builder collapses after query
   - Chart appears with smart default type
   - Click all 4 chart type buttons
   - Click table headers to sort
   - URL hash updates
6. Click "Modify Query" — verify builder expands
7. Copy URL with hash, paste in new tab — verify query restores
8. Switch language to Chinese — verify all new labels translate
9. Click "Clear All" — verify everything resets
10. Test on Finance domain (UNION query) and Schedule domain (is_absent subquery)

- [ ] **Step 2: Fix any issues found**

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(bi): complete BI Explorer UI/UX improvements

6 data domains, chart type selector, collapsible query builder,
table sorting, quick presets, URL state persistence, full EN/ZH i18n."
```
