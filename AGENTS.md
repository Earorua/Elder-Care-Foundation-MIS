# AGENTS.md

## Scope
These instructions apply to the whole repository.

This project is a Flask-based Management Information System for an elder care
foundation. It uses Jinja templates, Bootstrap 5, Flask-Login, direct SQLite
access, and a bundled `elder_care.db` database. Keep changes small, local to the
requested feature or fix, and consistent with the existing blueprint/template
patterns.

## Run And Test
- Install dependencies: `pip install -r requirements.txt`
- Start the app: `python app.py`
- Open locally: `http://127.0.0.1:5000`
- Run all tests: `python -m unittest discover`
- Run targeted tests: `python -m unittest tests.test_agent_helpers`

Use the seed users for manual checks:

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin123` | `admin` |
| `finance_user` | `finance123` | `finance` |
| `coordinator` | `coord123` | `event_coordinator` |
| `viewer` | `viewer123` | `viewer` |

## Project Structure
- `app.py`: app entry point, Flask-Login setup, seed users.
- `config.py`: database path, secret key, OpenRouter AI Agent config.
- `db.py`: SQLite connection and helper functions.
- `blueprints/`: Flask blueprints for auth, dashboard, donations, personnel,
  gifts, events, finance, BI Explorer, and AI Agent.
- `templates/`: Jinja2 templates grouped by module.
- `static/css/style.css`: main visual theme.
- `static/js/i18n.js`: client-side English/Chinese translations.
- `tests/`: unittest-based regression tests.
- `elder_care.db`: bundled SQLite database. Treat it as project data, but do
  not overwrite unrelated local edits.

## Database Rules
- Use direct SQLite access. Do not introduce an ORM unless explicitly requested.
- Prefer parameterized SQL for user input.
- The `User` table name is uppercase and must be quoted in SQL.
- `schedules.is_absent` has a trailing tab character; use `"is_absent\t"`.
- Preserve existing misspellings: `events.decription`,
  `other_income.recevied_date`, and `schedules.availibile_time`.
- `grants.grant_id` is a non-autoincrement primary key; CRUD uses `rowid`.
- `persons` and `donors` both include `marital_status`.
- `suppliers` includes `contact_name`.
- Donor/person marital status is synchronized when first name, last name, and
  email match after case-insensitive trimming.

## Access Control
- Use `role_required(*roles)` from `blueprints/auth.py` after `@login_required`.
- `User.has_role(*roles)` auto-grants access for `admin`.
- Role boundaries:
  - `finance`: donations and finance.
  - `event_coordinator`: personnel, gifts, and events.
  - `viewer`: dashboard only.
  - `admin`: all modules.
- Keep sidebar visibility in `templates/base.html` aligned with route
  permissions.

## Frontend And I18n
- Follow the existing Bootstrap/Jinja style and the "Botanical Warmth" theme.
- Add new user-facing text to `static/js/i18n.js` when adding or changing UI
  labels, placeholders, titles, flash messages, chart labels, or dynamic text.
- Use existing `data-i18n`, `data-i18n-placeholder`, `data-i18n-title`, and
  `data-i18n-html` attributes where appropriate.
- Keep chart labels and dynamic JavaScript text routed through `I18n.t(...)`
  when the surrounding code already does so.
- Avoid broad CSS rewrites. Reuse existing classes and variables unless a
  localized addition is needed.

## AI Agent
- The AI Agent lives in `blueprints/agent.py` and `templates/agent/index.html`.
- It should only execute read-only SQLite `SELECT` or `WITH` statements.
- Keep row limits enforced through `AGENT_ROW_LIMIT`.
- Do not commit API keys. `OPENROUTER_API_KEY` must come from the environment or
  a local-only config edit that is not committed.
- Defaults in `config.py`:
  - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
  - `OPENROUTER_MODEL=anthropic/claude-sonnet-4.6`
  - `OPENROUTER_TIMEOUT=120`

## Testing Expectations
- Add or update focused tests for behavior changes.
- Prefer the existing unittest style in `tests/`.
- For database behavior, use temporary test databases where the existing tests
  do so. Avoid tests that mutate the bundled `elder_care.db` unless the task is
  explicitly about bundled data.
- For template/i18n changes, mirror the existing tests that assert required
  hooks and translation keys.
- Run `python -m unittest discover` before claiming a change is complete when
  feasible.

## Documentation
- Update `USER_MANUAL.md` for user-visible workflow or configuration changes.
- Update `CLAUDE.md` when project architecture, commands, database quirks, roles,
  or major completed work change.
- Keep documentation concise and factual. Do not include secrets or local-only
  credentials.

## Git And Local Changes
- Check `git status --short --branch` before editing.
- Do not revert, overwrite, or stage unrelated user changes.
- If `elder_care.db` is already modified and the task does not require database
  changes, leave it untouched.
- Before committing or pushing, scan staged changes for secrets and run the
  relevant tests.
