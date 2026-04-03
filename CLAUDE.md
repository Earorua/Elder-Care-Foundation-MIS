# Elder Care Foundation MIS

## Overview
Flask-based Management Information System for an elder care foundation. Connects to an SQLite database (19 tables), providing CRUD management across 6 modules: Dashboard, Donations, Personnel, Gifts, Events, and Finance. Features RBAC access control and GAAS-compliant financial reports.

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
- Blueprint route permissions: donations/finance -> `finance`, events/personnel/gifts -> `event_coordinator`, dashboard -> all roles
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
│   └── finance.py          # Grants/other income/reports overview + 3 sub-reports (finance role)
├── templates/
│   ├── base.html           # Layout: sidebar + sticky topbar (breadcrumb + clock) + watermark footer
│   ├── auth/login.html     # Split-panel login: left branding + right form
│   ├── auth/users.html     # User management page (admin only)
│   ├── dashboard/index.html # Dashboard with animated stat cards + 6 chart cards
│   ├── donations/          # donations, donors, categories, feedback, receipts
│   ├── personnel/          # persons, schedules, payments
│   ├── gifts/              # gifts, batches, distribution, delivery, suppliers
│   ├── events/             # events, donors_events
│   └── finance/            # grants, other_income, reports, income_statement, balance_sheet, expenditure
└── static/
    ├── css/style.css       # "Botanical Warmth" theme — Playfair Display + Outfit, sage/terracotta/gold palette
    └── img/logo.png        # Transparent-background logo (auto-generated from elder_care_logo.png)
```

## UI/Design System — "Botanical Warmth"
- Typography: Playfair Display (headings, serif) + Outfit (body, sans-serif), loaded via Google Fonts
- Palette: sage green (`#5a8a6a`), terracotta (`#c07a56`), gold (`#c8a45c`), cream bg (`#f6f3ee`), warm card bg (`#fffdf9`)
- Sidebar: deep forest green gradient, gold accent hover/active states, JS-based active link tracking
- Topbar: sticky, frosted glass effect, breadcrumb navigation + live clock; each template defines `{% block breadcrumb %}` for page name
- Login: split-panel layout — left branding panel with floating shape animations, right form panel
- Tables: custom `table-header` class (replaces Bootstrap `table-dark`), gradient green header with rounded corners
- Charts: warm palette (`#5a8a6a`, `#c07a56`, `#c8a45c`, `#8a6dab`), Outfit font, semi-transparent bars with rounded corners
- Animations: `fade-in` + `fade-in-d1..d5` staggered delays, modal bounce easing, content area fade-in
- CSS variables defined in `:root` in `style.css` for consistent theming

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
