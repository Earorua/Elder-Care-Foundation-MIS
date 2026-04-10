# BI Explorer UI/UX Improvements — Design Spec

**Date:** 2026-04-10
**Status:** Draft
**Scope:** Expand BI Explorer from 2 to 6 data domains, add chart type selection, collapsible query builder, table sorting, quick presets, URL query state, and full bilingual i18n.

---

## Problem Statement

The current BI Explorer covers only 2 of 6 data modules (Donors, Personnel), offers only bar charts, has no query persistence, no drill-down, a rigid three-column layout that wastes space below the fold, no data previews, and no table sorting. These limitations make it a proof-of-concept rather than a useful analytics tool.

### Pain Points

| # | Pain Point | Evidence |
|---|---|---|
| P1 | Only 2 of 6 data domains available | `bi.py` only defines `DONOR_BASE` and `PERSON_BASE` |
| P2 | Only bar charts — no chart type selection | `renderChart()` hardcodes `type: 'bar'` |
| P3 | No query persistence — page reload loses all selections | No localStorage/URL/DB save logic |
| P4 | No drill-down on chart/table elements | No click handlers |
| P5 | Three-column layout always visible, pushes results below fold | All panels in `row g-3` with no collapse |
| P6 | No data preview before running query | No field-value previews or record count hints |
| P7 | Table lacks sorting and pagination | Plain DOM table rendering |

### Approach Considered and Rejected

**Cross-Domain Joins (Approach C):** A visual JOIN builder for arbitrary cross-table queries was considered but rejected. The added complexity (arbitrary join paths, security model changes, confusing UI for non-technical users) far exceeds the value for a small SQLite app with ~100 rows per table. The 6 predefined domains with their pre-built JOINs cover all realistic analysis needs.

**Minimal Polish (Approach A):** Fixing only chart types and sorting without adding new domains was considered but rejected because the biggest user gap is that 4 of 6 modules have zero BI coverage.

---

## Design

### 1. New Data Domains

Add 4 new domains to complement existing `donor` and `person` domains.

#### 1.1 Event Domain (`event`)

**Base SQL:**
```sql
FROM events e
LEFT JOIN donors_events de ON e.event_id = de.event_id
LEFT JOIN donors dn ON de.donor_id = dn.donor_id
```

**Filters:**

| Key | Label | Type | SQL |
|-----|-------|------|-----|
| `event_type` | Event Type | enum (DB-sourced) | `e.event_type` |
| `event_status` | Event Status | enum: Planned, Ongoing, Completed, Cancelled | `e.status` |
| `event_location` | Event Location | enum (DB-sourced) | `e.location` |
| `event_date` | Event Date | daterange | `e.start_date` |
| `target_amount` | Target Amount | range | `e.target_amount` |

**Dimensions:**

| Key | Label | SQL | Alias |
|-----|-------|-----|-------|
| `event_type` | Event Type | `e.event_type` | `event_type` |
| `event_status` | Event Status | `e.status` | `event_status` |
| `event_location` | Event Location | `e.location` | `event_location` |
| `event_year` | Event Year | `strftime('%Y', e.start_date)` | `event_year` |

**Metrics:**

| Key | Label | SQL | Format |
|-----|-------|-----|--------|
| `event_count` | Event Count | `COUNT(DISTINCT e.event_id)` | integer |
| `participant_count` | Participant Count | `COUNT(DISTINCT de.donor_id)` | integer |
| `total_target` | Total Target Amount | `SUM(e.target_amount)` | currency |
| `total_actual` | Total Actual Amount | `SUM(e.actual_amount)` | currency |
| `avg_target` | Avg Target Amount | `AVG(e.target_amount)` | currency |
| `achievement_rate` | Achievement Rate | `ROUND(SUM(e.actual_amount)*100.0/NULLIF(SUM(e.target_amount),0), 1)` | percent_val |

#### 1.2 Gift Domain (`gift`)

**Base SQL:**
```sql
FROM gifts g
LEFT JOIN gift_batch gb ON g.gift_id = gb.gift_id
LEFT JOIN gift_distribution gd ON gb.batch_id = gd.batch_id
```

**Filters:**

| Key | Label | Type | SQL |
|-----|-------|------|-----|
| `gift_type` | Gift Type | enum (DB-sourced) | `g.gift_type` |
| `gift_active` | Gift Active | bool | `g.is_active` |
| `unit_cost` | Unit Cost | range | `g.unit_cost` |
| `is_free` | Free Distribution | bool | `gd.is_free` |

**Dimensions:**

| Key | Label | SQL | Alias |
|-----|-------|-----|-------|
| `gift_type` | Gift Type | `g.gift_type` | `gift_type` |
| `gift_active_dim` | Gift Active | `CASE g.is_active WHEN 1 THEN 'Active' ELSE 'Inactive' END` | `gift_active` |
| `is_free_dim` | Distribution Type | `CASE gd.is_free WHEN 1 THEN 'Free' ELSE 'Donor Gift' END` | `distribution_type` |

**Metrics:**

| Key | Label | SQL | Format |
|-----|-------|-----|--------|
| `gift_count` | Gift Count | `COUNT(DISTINCT g.gift_id)` | integer |
| `total_stock` | Total Stock | `SUM(g.current_stock)` | integer |
| `total_distributed` | Total Distributed | `SUM(gd.quantity)` | integer |
| `total_inventory_value` | Inventory Value | `SUM(g.current_stock * g.unit_cost)` | currency |
| `avg_unit_cost` | Avg Unit Cost | `AVG(g.unit_cost)` | currency |

#### 1.3 Finance Domain (`finance`)

**Base SQL:**
```sql
FROM (
  SELECT grant_name AS name, 'Grant' AS source_type,
         funding_org AS source, amount, received_date AS received
  FROM grants
  UNION ALL
  SELECT income_name, 'Other' AS source_type,
         source_name, amount, recevied_date
  FROM other_income
) f
```

Note: `recevied_date` preserves the existing database column typo. The `source_type` column is explicitly set to `'Grant'` or `'Other'` (not derived from `income_type`) so the enum filter works correctly.

**Filters:**

| Key | Label | Type | SQL |
|-----|-------|------|-----|
| `source_type` | Source Type | enum: Grant, Other | `f.source_type` |
| `finance_amount` | Amount | range | `f.amount` |
| `finance_date` | Received Date | daterange | `f.received` |

**Dimensions:**

| Key | Label | SQL | Alias |
|-----|-------|-----|-------|
| `finance_source_type` | Source Type | `f.source_type` | `source_type` |
| `finance_source` | Source | `f.source` | `source` |
| `finance_year` | Year | `strftime('%Y', f.received)` | `finance_year` |

**Metrics:**

| Key | Label | SQL | Format |
|-----|-------|-----|--------|
| `income_count` | Income Count | `COUNT(*)` | integer |
| `total_income` | Total Income | `SUM(f.amount)` | currency |
| `avg_income` | Avg Income | `AVG(f.amount)` | currency |
| `max_income` | Max Income | `MAX(f.amount)` | currency |
| `min_income` | Min Income | `MIN(f.amount)` | currency |

#### 1.4 Schedule Domain (`schedule`)

**Base SQL:**
```sql
FROM (SELECT *, "is_absent\t" AS is_absent FROM schedules) s
LEFT JOIN persons p ON s.person_id = p.person_id
LEFT JOIN events e ON s.event_id = e.event_id
```

Note: The `schedules.is_absent` column has a trailing tab character in the actual column name (a schema defect). The subquery aliases it to a clean `is_absent` so all downstream filter/dimension/metric SQL can use `s.is_absent` without quoting the tab character everywhere.

**Filters:**

| Key | Label | Type | SQL |
|-----|-------|------|-----|
| `shift_date` | Shift Date | daterange | `s.shift_date` |
| `schedule_status` | Status | enum: Scheduled, In Progress, Completed, Absent | `s.status` |
| `is_absent_filter` | Absent | bool | `s.is_absent` |
| `overtime` | Overtime (hrs) | range | `s.overtime` |

**Dimensions:**

| Key | Label | SQL | Alias |
|-----|-------|-----|-------|
| `schedule_status_dim` | Schedule Status | `s.status` | `schedule_status` |
| `is_absent_dim` | Attendance | `CASE s.is_absent WHEN 1 THEN 'Absent' ELSE 'Present' END` | `attendance` |
| `shift_month` | Shift Month | `strftime('%Y-%m', s.shift_date)` | `shift_month` |
| `schedule_event_name` | Event | `e.event_name` | `event_name` |
| `schedule_person_type` | Person Type | `p.person_type` | `person_type` |

**Metrics:**

| Key | Label | SQL | Format |
|-----|-------|-----|--------|
| `shift_count` | Shift Count | `COUNT(*)` | integer |
| `absent_count` | Absent Count | `SUM(CASE s.is_absent WHEN 1 THEN 1 ELSE 0 END)` | integer |
| `total_overtime` | Total Overtime | `SUM(s.overtime)` | integer |
| `attendance_rate` | Attendance Rate | `ROUND((1.0 - CAST(SUM(CASE s.is_absent WHEN 1 THEN 1 ELSE 0 END) AS REAL) / NULLIF(COUNT(*), 0)) * 100, 1)` | percent_val |

### 2. Chart Type Selector

A row of 4 icon buttons in the chart card header, styled as toggles:

| Type | Icon | When auto-suggested |
|------|------|-------------------|
| Bar | `bi-bar-chart-fill` | Default for most queries |
| Horizontal Bar | `bi-bar-chart-steps` | When avg label length > 12 characters |
| Doughnut | `bi-pie-chart-fill` | Single metric + single dimension + ≤8 rows |
| Line | `bi-graph-up` | When dimension is temporal (year/month) |

**Smart default algorithm:**
```
if dimension alias contains 'year' or 'month' → Line
else if metCols.length === 1 && rows.length <= 8 → Doughnut
else if avg(labels.map(l => l.length)) > 12 → Horizontal Bar
else → Bar
```

User can always override by clicking a different toggle. The active toggle uses the accent color fill; inactive toggles are outline style.

**Implementation:** Add a `chartType` state variable. The `renderChart()` function reads this variable. Chart type buttons call `renderChart()` with the new type without re-querying. Doughnut chart uses only the first metric column.

### 3. Collapsible Query Builder

**Behavior:**
- After a query runs successfully, the three-panel row (Filters/Dimensions/Metrics) and the domain selector card animate to collapse height with a 300ms ease transition
- A "query summary bar" appears showing the current query as inline tags: domain pill + dimension tags (terracotta) + metric tags (gold) + active filter count badge
- A "Modify Query" button expands the panels back
- The action bar (Run Query / Clear All / Export CSV) remains visible in both states

**CSS implementation:**
- `.bi-builder-wrap` wrapper div with `max-height` transition
- `.bi-builder-wrap.collapsed` sets `max-height: 0; overflow: hidden; opacity: 0`
- `.bi-query-summary` bar with `display: none` by default, shown when collapsed
- Summary bar uses the same tag pill styles as the multiselect triggers

### 4. Table Column Sorting

**Behavior:**
- Each `<th>` in the result table is clickable
- Click cycles: unsorted → ascending → descending → unsorted
- Sort indicator: `bi-chevron-up` (asc) / `bi-chevron-down` (desc) icon appended to the active header
- Sort is client-side using `Array.sort()` on the in-memory `rows` data
- Numeric columns (currency/integer/percent) sort numerically; text columns sort alphabetically (locale-aware)
- Sort state resets when a new query runs

**CSS:**
- `.bi-sortable` class on `<th>` elements: `cursor: pointer; user-select: none;`
- `.bi-sort-icon` positioned right of header text, 0.7rem, muted color, transitions opacity

### 5. Quick Presets

A horizontally scrollable row of preset pills displayed above the domain selector card.

**6 presets:**

| Label | Domain | Dims | Metrics | i18n ZH |
|-------|--------|------|---------|---------|
| Donations by Type | donor | donation_type | donor_count, total_donation | 按类型统计捐款 |
| Donors by Location | donor | donor_location | donor_count, total_donation | 按地区统计捐赠者 |
| Staff Payments | person | person_role | person_count, total_payment | 员工薪酬统计 |
| Events Overview | event | event_type | event_count, total_actual | 活动概览 |
| Gift Inventory | gift | gift_type | gift_count, total_stock, total_inventory_value | 礼品库存 |
| Income Sources | finance | finance_source_type | income_count, total_income | 收入来源 |

**Behavior:**
- Clicking a preset sets the domain, populates dimensions and metrics, clears filters, and immediately runs the query
- Active preset gets a filled background; clicking it again resets to manual mode
- Presets defined as a JS constant array so they're easy to maintain

**CSS:** `.bi-preset-pill` outline button with accent border, small rounded pill shape, horizontal scrollable container with `overflow-x: auto; white-space: nowrap; gap: 8px`.

### 6. URL Query State

**Encoding:**
- After a successful query, encode the state as JSON and base64 it into the URL hash:
  ```
  #q=eyJkb21haW4iOiJkb25vciIsImRpbWVuc2lvbnMiOlsiZG9ub3JfZ2VuZGVyIl0sIm1ldHJpY3MiOlsiZG9ub3JfY291bnQiXSwiZmlsdGVycyI6e319
  ```
- State object shape: `{ domain, dimensions: [], metrics: [], filters: {} }`

**Decoding:**
- On `DOMContentLoaded`, check for `location.hash` starting with `#q=`
- If found, decode, restore all selections (domain radio, selected dims/mets, filter values), and auto-run the query
- If hash is invalid or references unknown fields, silently ignore and show default state

**No server changes needed** — this is purely client-side.

### 7. Bilingual i18n

All new strings get entries in the `ZH` dictionary in `static/js/i18n.js`.

**New keys (~50):**

Domain labels:
- `'Events'` → `'活动'`
- `'Gifts'` → `'礼品'`
- `'Finance'` → `'财务'`
- `'Schedules'` → `'排班'`

Filter/Dimension/Metric labels for all 4 new domains (see domain definitions above for the full list).

UI strings:
- `'Modify Query'` → `'修改查询'`
- `'Presets'` → `'预设查询'`
- `'Bar Chart'` → `'柱状图'`
- `'Horizontal Bar'` → `'条形图'`
- `'Doughnut Chart'` → `'饼图'`
- `'Line Chart'` → `'折线图'`
- `'Sort ascending'` → `'升序排列'`
- `'Sort descending'` → `'降序排列'`
- All 6 preset labels (see table above)
- Domain descriptions for the domain selector tooltips

### 8. API Contract Change

The `/api/bi/query` POST body gains a new required field `domain`:

```json
{
  "domain": "donor",
  "filters": { ... },
  "dimensions": ["donation_type"],
  "metrics": ["donor_count", "total_donation"]
}
```

Valid domain values: `donor`, `person`, `event`, `gift`, `finance`, `schedule`.

The server validates `domain` against the known list. If missing or invalid, falls back to the existing `_detect_domain()` auto-detection for backward compatibility. When present, the server uses it directly — this eliminates ambiguity when fields from different domains share similar names.

The frontend `collectParams()` function is updated to include `domain: currentDomain` in the returned object.

---

## Files Changed

| File | Type | Changes |
|------|------|---------|
| `blueprints/bi.py` | Modified | Add 4 new domain definitions (FILTER_DEFS, DIMENSION_DEFS, METRIC_DEFS entries), add EVENT_BASE/GIFT_BASE/FINANCE_BASE/SCHEDULE_BASE SQL, update `_detect_domain()` to check all 6 domains (the UI now sends the domain explicitly via the domain radio selector, so `_detect_domain` serves only as a fallback validation — the frontend-selected domain takes priority), update `_build_query()` base selection, add presets list endpoint |
| `templates/bi/index.html` | Modified | Domain selector expanded to 6 buttons (2 rows of 3), preset pills row, chart type toggle buttons, collapsible query builder wrapper + summary bar, sortable table headers, URL hash encode/decode logic |
| `static/js/i18n.js` | Modified | ~50 new ZH translation keys for domains, fields, UI strings, presets |
| `static/css/style.css` | Modified | ~80 new lines: chart type toggle styles, collapsible panel transitions, sort indicator styles, preset pill styles, 6-domain button grid |

---

## Out of Scope

- Cross-domain joins (arbitrary table combinations)
- Server-side saved queries (DB persistence)
- Drill-down (clicking chart bars to filter)
- Pagination (dataset sizes are small enough for client-side rendering)
- New chart types beyond bar/horizontal/doughnut/line (e.g., scatter, area)
- Dashboard integration (embedding BI queries in dashboard widgets)
