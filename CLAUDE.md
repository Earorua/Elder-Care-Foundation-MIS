# Elder Care Foundation MIS

## Overview
Flask-based Management Information System for an elder care foundation. Connects to an SQLite database (19 tables), providing CRUD management across 6 modules: Dashboard, Donations, Personnel, Gifts, Events, and Finance. Features RBAC access control and GAAS-compliant financial reports.

## Tech Stack
- Flask + Jinja2 + Flask-Login
- Bootstrap 5 + Bootstrap Icons + Chart.js (all via CDN)
- SQLite3 direct connection, no ORM

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
│   ├── base.html           # Layout + role-conditional sidebar + watermark footer
│   ├── auth/login.html
│   ├── auth/users.html     # User management page (admin only)
│   ├── dashboard/index.html
│   ├── donations/          # donations, donors, categories, feedback, receipts
│   ├── personnel/          # persons, schedules, payments
│   ├── gifts/              # gifts, batches, distribution, delivery, suppliers
│   ├── events/             # events, donors_events
│   └── finance/            # grants, other_income, reports, income_statement, balance_sheet, expenditure
└── static/
    ├── css/style.css       # Modern theme styles
    └── img/logo.png        # Transparent-background logo (auto-generated from elder_care_logo.png)
```

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
4. UI polish: gradient sidebar, modern card styles, Inter font, full-screen gradient login background
5. Database path set to `elder_care.db`, added birthday/gender/contact_name field support
6. Populated complete sample data for all 19 tables
7. RBAC access control: `role_required` decorator + sidebar role-conditional rendering + 4 roles (admin/finance/event_coordinator/viewer)
8. User management page (/users): admin-only, supports add/edit role/reset password/enable-disable/delete users
9. 4 seed users auto-created (admin, finance_user, coordinator, viewer)
10. Financial reports system with GAAS-compliant naming: reports overview (/reports) + 3 sub-reports
    - Statement of Activities (/reports/income-statement): revenue by donation type/funding org/income type + expense detail + net income + monthly trend chart
    - Statement of Financial Position (/reports/balance-sheet): cash + gift inventory value + inventory detail + asset composition doughnut chart
    - Statement of Functional Expenses (/reports/expenditure): category summary cards + distribution pie chart + monthly trend chart + personnel compensation detail
11. Written complete user manual (USER_MANUAL.md)
12. Database file bundled in project directory, path changed from `BASE_DIR/../` to `BASE_DIR/`, project is self-contained
13. Full English localization: all flash messages, UI labels, form elements, and page titles translated from Chinese to English
14. Custom logo: sidebar brand uses transparent-background logo (`static/img/logo.png`, generated from `elder_care_logo.png` with white background removed); logo watermark (opacity 0.08) displayed at the bottom of every authenticated page
15. Dashboard chart layout optimization: reorganized from uniform 2×3 grid to compact 3-row layout (8:4 + 4:4:4 + 12), fixed chart heights (260/220px), `maintainAspectRatio:false`, doughnut legends moved to bottom — eliminates whitespace waste
16. Sidebar brand styling: title gradient updated to 3-color blue→purple→pink (`#60a5fa→#a78bfa→#f0abfc`), font enlarged to 1.35rem/800 weight, logo enlarged to 44×44px
