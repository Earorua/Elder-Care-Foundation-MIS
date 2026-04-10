# Elder Care Foundation MIS

## Overview
Flask-based Management Information System for an elder care foundation. Connects to an SQLite database (19 tables), providing CRUD management across 7 modules: Dashboard, Donations, Personnel, Gifts, Events, Finance, and BI Explorer. Features RBAC access control, GAAS-compliant financial reports, and a dynamic BI query builder.

## Tech Stack
- Flask + Jinja2 + Flask-Login
- Bootstrap 5 + Bootstrap Icons + Chart.js (all via CDN)
- Google Fonts: Playfair Display (headings) + Outfit (body)
- SQLite3 direct connection, no ORM
- Git version control (local)

## Database
- File: `elder_care.db` (bundled in the project directory)
- Referenced in config.py via `os.path.join(BASE_DIR, 'elder_care.db')`
- `"User"` table name is uppercase; must be quoted in SQL
- `schedules.is_absent` column has a trailing tab character; use `"is_absent\t"` in SQL
- Misspelled column names preserved as-is: `events.decription`, `other_income.recevied_date`, `schedules.availibile_time`
- `grants.grant_id` is a non-autoincrement primary key (pk=0); CRUD uses `rowid` instead
- `persons` table has extra `birthday`, `gender` columns
- `suppliers` table has extra `contact_name` column
- On startup, automatically adds `role` column to User table and creates/updates admin user (admin / admin123)
- On startup, automatically creates 4 seed users: admin, finance_user, coordinator, viewer

## RBAC Access Control
- `role_required(*roles)` decorator defined in `blueprints/auth.py`, stacked after `@login_required`
- `User.has_role(*roles)` method auto-grants access to admin role
- Role definitions: admin (all), finance (donations + finance), event_coordinator (personnel + gifts + events), viewer (dashboard only)
- Sidebar in `base.html` uses `{% if current_user.has_role(...) %}` for role-conditional navigation rendering
- Blueprint route permissions: donations/finance -> `finance`, events/personnel/gifts -> `event_coordinator`, dashboard -> all roles, bi -> all roles
- User management page `/users` (admin only): add/edit role/reset password/enable-disable/delete users

## Seed Users
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| finance_user | finance123 | finance |
| coordinator | coord123 | event_coordinator |
| viewer | viewer123 | viewer |

## Project Structure
```
C:\Users\XF\Desktop\elder_care_gui\
├── app.py                  # Entry point + Flask-Login + seed users (4)
├── config.py               # DB path, secret key
├── db.py                   # get_db / query_db / execute_db
├── elder_care.db           # SQLite database file (bundled)
├── elder_care_logo.png     # Original logo source image
├── requirements.txt        # Flask, Flask-Login
├── USER_MANUAL.md          # User manual
├── blueprints/
│   ├── auth.py             # Login/logout + role_required decorator + user management CRUD
│   ├── dashboard.py        # Dashboard + 6 chart APIs
│   ├── donations.py        # Donations/donors/categories/feedback/tax receipts (finance role)
│   ├── personnel.py        # Persons/schedules/payments (event_coordinator role)
│   ├── gifts.py            # Gifts/batches/distribution/delivery/suppliers (event_coordinator role)
│   ├── events.py           # Events/donor participation (event_coordinator role)
│   ├── finance.py          # Grants/other income/reports overview + 3 sub-reports (finance role)
│   └── bi.py               # BI Explorer: whitelist defs (46 dims, 30+ metrics, 6 domains) + query builder + API
├── templates/
│   ├── base.html           # Layout: sidebar + sticky topbar (breadcrumb + clock) + watermark footer
│   ├── auth/login.html     # Split-panel login: left branding + right form
│   ├── auth/users.html     # User management page (admin only)
│   ├── dashboard/index.html # Dashboard with animated stat cards + 6 chart cards
│   ├── donations/          # donations, donors, categories, feedback, receipts
│   ├── personnel/          # persons, schedules, payments
│   ├── gifts/              # gifts, batches, distribution, delivery, suppliers
│   ├── events/             # events, donors_events
│   ├── finance/            # grants, other_income, reports, income_statement, balance_sheet, expenditure
│   └── bi/index.html       # BI Explorer: domain selector, filter/dimension/metric panels, chart + table
└── static/
    ├── css/style.css       # "Botanical Warmth" theme — Playfair Display + Outfit, sage/terracotta/gold palette
    ├── js/i18n.js          # Bilingual i18n engine (EN/ZH): translation dict + DOM auto-apply + language toggle
    └── img/logo.png        # Transparent-background logo (auto-generated from elder_care_logo.png)
```

## UI/Design System — "Botanical Warmth"
- Typography: Playfair Display (headings, serif) + Outfit (body, sans-serif), loaded via Google Fonts
- Palette: sage green (`#5a8a6a`), terracotta (`#c07a56`), gold (`#c8a45c`), cream bg (`#f6f3ee`), warm card bg (`#fffdf9`)
- Sidebar: deep forest green gradient, gold accent hover/active states, JS-based active link tracking, ripple effect on click, special logout link styling (red tint hover)
- Topbar: sticky, frosted glass morphism (blur 20px + saturate 1.8), breadcrumb navigation + live clock + user avatar; each template defines `{% block breadcrumb %}` for page name
- Login: split-panel layout — left branding panel with floating shape animations + leaf particle effects + system stats (6 Modules / 19 Tables / 4 Roles), right form panel with password visibility toggle + remember me checkbox + security footer
- Tables: custom `table-header` class (replaces Bootstrap `table-dark`), gradient green header with rounded corners, row hover gradient animation with indent effect, `table-info-bar` wrapper for search + metadata
- Charts: warm palette (`#5a8a6a`, `#c07a56`, `#c8a45c`, `#8a6dab`), Outfit font, semi-transparent bars with rounded corners, custom dark tooltips with currency formatting
- Animations: `fade-in` + `fade-in-d1..d5` staggered delays, modal bounce easing, content area fade-in, stat card pulse, alert slide-in
- Cards: warm border transitions on hover, stat cards with gradient top-border + radial glow effect on hover, report-link-cards with top border slide-in animation
- Badges: gradient backgrounds for all variants (success/primary/danger/warning/info), record-count pill badges on all CRUD page headers
- Modals: backdrop blur, gradient header, centered delete confirmation with icon illustration
- Empty states: dashed border, gradient icon, centered layout with descriptive text
- Forms: enhanced focus rings (double shadow), custom validation colors
- Print: optimized styles for financial reports (hide nav/charts, proper font sizing)
- Responsive: sidebar overlay on mobile, topbar hamburger toggle, content area padding adjustments, stat card resizing
- Accessibility: skip-link, focus-visible outlines, reduced-motion media query support
- CSS variables defined in `:root` in `style.css` for consistent theming (~1500 lines)

## Bilingual i18n System (EN/ZH)
- `static/js/i18n.js`: client-side translation engine loaded in `base.html` `<head>`
- Translation dict `ZH` maps English keys to Chinese; English is the default/fallback
- Language state persisted in `localStorage` key `ecmis_lang` (`'en'` or `'zh'`)
- API: `I18n.t(key)` returns translated string; `I18n.getLang()` returns current lang; `I18n.setLang(lang)` switches and reloads
- DOM attributes: `data-i18n` (textContent), `data-i18n-placeholder` (placeholder), `data-i18n-title` (tooltip title), `data-i18n-html` (innerHTML)
- `I18n.applyAll()` runs on DOMContentLoaded, translating all `[data-i18n*]` elements
- Language toggle button (`#langToggleBtn`) in topbar and login page, styled via `.lang-toggle-btn` in CSS
- Chart data labels from API (e.g. "Cash", "Male") translated via `d.labels.map(l=>I18n.t(l))` in dashboard JS
- Topbar clock and dashboard timestamp use `I18n.getLang()` to switch locale between `en-US` and `zh-CN`
- Flash messages use `data-i18n="{{ message }}"` in base.html for client-side translation of server-side messages
- Adding new translations: add English key + Chinese value to the `ZH` dict in `i18n.js`

## How to Run
```bash
cd C:\Users\XF\Desktop\elder_care_gui
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000 in browser, login with admin / admin123
```

## Completed Work
1. Built complete Flask project framework (8 blueprints, 20+ template pages)
2. Dashboard with 4 stat cards + 6 Chart.js charts (doughnut + bar)
3. Full CRUD for all 19 tables, each page with data table + Bootstrap Modal forms
4. Database path set to `elder_care.db`, added birthday/gender/contact_name field support
5. Populated complete sample data for all 19 tables
6. RBAC access control: `role_required` decorator + sidebar role-conditional rendering + 4 roles (admin/finance/event_coordinator/viewer)
7. User management page (/users): admin-only, supports add/edit role/reset password/enable-disable/delete users
8. 4 seed users auto-created (admin, finance_user, coordinator, viewer)
9. Financial reports system with GAAS-compliant naming: reports overview (/reports) + 3 sub-reports
    - Statement of Activities (/reports/income-statement): revenue by donation type/funding org/income type + expense detail + net income + monthly trend chart
    - Statement of Financial Position (/reports/balance-sheet): cash + gift inventory value + inventory detail + asset composition doughnut chart
    - Statement of Functional Expenses (/reports/expenditure): category summary cards + distribution pie chart + monthly trend chart + personnel compensation detail
10. Written complete user manual (USER_MANUAL.md)
11. Database file bundled in project directory, path changed from `BASE_DIR/../` to `BASE_DIR/`, project is self-contained
12. Full English localization: all flash messages, UI labels, form elements, and page titles translated from Chinese to English
13. Custom logo: sidebar brand uses transparent-background logo (`static/img/logo.png`); logo watermark displayed at the bottom of every authenticated page
14. Dashboard chart layout optimization: 3-row layout (8:4 + 4:4:4 + 12), fixed chart heights, `maintainAspectRatio:false`
15. Visual theme v1 "Warm Institutional Elegance": DM Serif Display + DM Sans, sage/terracotta/cream palette, centered sidebar brand
16. Visual theme v2 "Botanical Warmth": Playfair Display + Outfit fonts, split-panel login page with animated floating shapes, sticky topbar with breadcrumb navigation + live clock, sidebar active state tracking via JS, stat cards with gradient top-border accents, chart cards with colored icon badges, enhanced modal bounce animations, staggered fade-in animations, breadcrumb blocks on all 24 templates, responsive mobile support
17. Git version control initialized with local repository
18. Visual theme v3 "Botanical Warmth — Refined": comprehensive UI polish pass
    - CSS (~460 new lines): glass morphism topbar, table row hover micro-interactions (gradient + indent), gradient badges, stat card radial glow, record-count pill badges, enhanced empty states (dashed border + gradient icons), status indicator dots, modal backdrop blur, enhanced form focus rings, custom dark tooltips, section dividers, sidebar logout special styling, action button gradient polish, print style improvements, chart card title border-bottom
    - Dashboard: time-of-day welcome greeting ("Good morning/afternoon/evening, username"), stat trend indicators below each metric, single data-updated timestamp in page header
    - Login page: password visibility toggle (eye icon), remember me checkbox, floating leaf particle animations on branding panel, system stats display (6 Modules / 19 Tables / 4 Roles), security footer ("Protected by role-based access control")
    - All 18 CRUD pages: record count badges in page headers, unified `table-info-bar` wrapper, context-specific search placeholders
    - Financial reports overview: stat cards with icons + staggered fade-in, section dividers, icon container boxes for report link cards
    - All 3 financial report charts: custom tooltip configs (dark bg, currency formatting, Outfit font), rounded bars, warm palette, axis label callbacks
    - Delete confirmation modal: centered layout with icon circle illustration + separated warning text
19. Dashboard & module enhancements (v4)
    - Dashboard Financial Quick Access: finance summary stat cards (Total Revenue / Total Expenses / Net Income) + 3 report-link cards (Statement of Activities, Financial Position, Functional Expenses) visible to finance role
    - US Map Donor Visualization: replaced location bar chart with inline SVG US state map; states colored by donor density (sage green gradient); hover tooltips showing state name + donor count; legend showing total donors/states
    - Donor Location Dropdown: replaced free-text location input with US state dropdown (`<select>`) in donors add/edit form; migrated existing city-name data to state codes (NY, CA, TX, etc.); table displays full state name with code
    - Gift Distribution Chart: new horizontal bar chart on Dashboard showing distribution by gift type, split by Free Distribution vs Donor Gifts; data from `gift_distribution` table aggregated by `is_free` flag
    - New Gift Types Seeded: Picture Book (Education, $10, stock 120) and Postcard (Stationery, $2.50, stock 500) auto-seeded on startup
    - Schedule Monitor on Dashboard: stat cards showing upcoming events count + scheduled shifts count; link to Schedule Board page; visible to event_coordinator/admin roles
    - Schedule Board (`/schedule-board`): new Kanban-style page with event selector dropdown; selecting an event loads shifts via AJAX API and displays them in 4 columns (Scheduled / In Progress / Completed / Absent); each card shows person name, role, date, time range, overtime, notes
    - Sidebar: added Schedule Board link under Personnel section
    - CSS: Kanban board styles (~150 lines), US map tooltip styles, responsive grid for Kanban (4-col → 2-col → 1-col)
    - Backend: 3 new API endpoints (`/api/charts/location_map`, `/api/charts/gift_distribution`, `/api/schedule-board/<event_id>`); US_STATES dict in dashboard.py; schedule board routes in personnel.py
20. Bilingual i18n system (EN/ZH)
    - `static/js/i18n.js`: client-side translation engine with 200+ key-value pairs covering all UI text
    - All 26+ templates annotated with `data-i18n`, `data-i18n-placeholder`, `data-i18n-title` attributes
    - Language toggle button in topbar (authenticated pages) and login page; state persisted in localStorage
    - Dashboard chart legends translated: donation type (Cash/Check/Wire Transfer → 现金/支票/电汇), gender (Male/Female → 男/女)
    - Chart dataset labels, axis units, and tooltip text all pass through `I18n.t()` for bilingual display
    - Topbar clock and dashboard "Data updated" timestamp switch locale (`en-US` ↔ `zh-CN`) based on language
    - Flash messages (login page) rendered with `data-i18n` for client-side translation ("Logged out successfully", "Please log in first")
21. BI Explorer module (`/bi`)
    - Backend (`blueprints/bi.py`): whitelist-based query builder with 6 data domains (donor, person, event, gift, finance, schedule), 46 dimensions, 30+ metrics, 30+ filters; parameterised SQL generation with domain auto-detection; `/api/bi/query` POST endpoint + `/api/bi/meta` GET endpoint
    - Frontend (`templates/bi/index.html`): three-panel builder (Filters / Dimensions / Metrics) with multi-select dropdowns; domain selector radio buttons; 12 presets (6 basic + 6 comprehensive); collapsible query summary bar; sortable results table; CSV export
    - Chart system: 4 chart types (bar / horizontal bar / doughnut / line) with type toggle buttons; chart metric selector (multi-select dropdown to choose which metrics to chart); multi-axis support (each metric gets independent Y-axis with color-coded labels and formatted ticks to handle magnitude differences); 12-color palette
    - Doughnut chart enhancements: per-metric pagination with dot indicator + arrow navigation; title displays current metric name centered above chart; legend at bottom showing all dimension labels (multi-dim joined with `/`); tooltip shows value + percentage
    - URL hash state encoding (`#q=base64`) for shareable/bookmarkable queries; state restore on page load
    - CSS: doughnut pagination styles (nav buttons, dot indicators, labels), multi-select dropdown styles
    - i18n: all BI UI text, preset labels, and 50+ dimension/metric value translations added to `i18n.js`
22. Database fix: removed broken foreign key constraint on `donations.donation_type` that referenced empty table name `""`, causing "no such table: main." error when `PRAGMA foreign_keys = ON`
