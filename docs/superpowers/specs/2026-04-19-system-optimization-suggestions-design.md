# System Optimization Suggestions Design

## Goal

Add a "System Optimization Suggestions" workflow that lets any active logged-in user submit improvement suggestions from a page that is separate from the main module workspace, while allowing administrators to review those suggestions inside the main site.

The suggestion data must be shared between the separate submission page and the main admin module through the existing SQLite database.

## Scope

In scope:

- A login-required `/suggestions` page for submitting system optimization suggestions.
- Submission access for any authenticated account, regardless of role.
- A main-site administrator module for viewing submitted suggestions.
- Optional administrator status updates for tracking review progress.
- A new SQLite table for suggestion records.
- UI that reuses the existing Botanical Warmth styling, Bootstrap setup, logo, CSS variables, and language toggle behavior.
- i18n keys for all new user-facing labels, placeholders, buttons, status values, and flash messages.
- Focused tests for routing, permissions, persistence, template hooks, and i18n coverage.

Out of scope:

- Anonymous suggestions.
- Public unauthenticated submission.
- Changing the main site's existing visual theme.
- Adding a new visual theme switcher. The confirmed design keeps the main visual style unchanged and reuses the existing language toggle behavior.
- Email notifications, file attachments, threaded comments, voting, or duplicate detection.
- Full workflow/task management beyond a simple suggestion status.

## Access Rules

The submission page is independent from business modules but not anonymous:

- `GET /suggestions` requires login.
- `POST /suggestions` requires login.
- Any active authenticated user can submit, including `admin`, `finance`, `event_coordinator`, and `viewer`.
- If a visitor is not logged in, Flask-Login redirects to the existing login page and then returns to `/suggestions`.
- Submitters do not need to provide contact details because the record is associated with the logged-in account.

The admin review module is visible only to administrators:

- `GET /admin/suggestions` requires `@login_required` and `@role_required('admin')`.
- Optional status update actions also require administrator access.
- The admin sidebar gets a new "System Optimization Suggestions" link under Administration, shown only when `current_user.is_admin`.

## Architecture

Create a new blueprint, for example `blueprints/suggestions.py`, and register it in `app.py`.

Routes:

- `GET /suggestions`: render the separate submission page.
- `POST /suggestions`: validate and store a new suggestion from the current user.
- `GET /admin/suggestions`: render the administrator review list.
- `POST /admin/suggestions/<int:id>/status`: update a suggestion status, if status management is included.

Templates:

- `templates/suggestions/submit.html`: independent submission page that uses the same static CSS, Bootstrap, logo, fonts, and `i18n.js`, but does not need to appear as another business module workspace.
- `templates/suggestions/admin_list.html`: main-site admin page extending the normal authenticated shell.

The submission page may include a small top bar with the logo, current username, language toggle, dashboard link, and logout link. It should avoid duplicating the full main sidebar so the page remains a separate suggestion surface.

The admin list should follow existing table/list patterns used by modules such as user management and donor feedback.

## Data Model

Add a table such as `system_optimization_suggestions`.

Recommended fields:

- `suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `submitter_user_id INTEGER NOT NULL`
- `submitter_name TEXT NOT NULL`
- `submitter_role TEXT NOT NULL`
- `title TEXT NOT NULL`
- `category TEXT NOT NULL`
- `priority TEXT NOT NULL`
- `content TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'New'`
- `admin_notes TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

The table should preserve submitter username and role snapshots so historical records still show who submitted the suggestion even if the user's role changes later.

Use direct SQLite access, matching the rest of the project. The database initialization helper should create the table if it does not exist during app startup, without overwriting unrelated bundled database contents.

Suggested fixed values:

- Category: `Functionality`, `Usability`, `Performance`, `Data Quality`, `Security`, `Reporting`, `Other`.
- Priority: `Low`, `Medium`, `High`, `Urgent`.
- Status: `New`, `Reviewed`, `Planned`, `Resolved`.

Stored values should be stable canonical strings. Display text should use i18n keys.

## Submission UI

The `/suggestions` page is a focused work surface, not a marketing page.

Main elements:

- Page title: "System Optimization Suggestions".
- Short operational copy explaining that logged-in users can submit improvement ideas for administrators to review.
- Form fields:
  - Title.
  - Category.
  - Priority.
  - Suggestion details.
- Submit button.
- Confirmation flash after successful submission.
- Current user indicator so submitters understand which account will be attached to the suggestion.

Validation:

- Title is required and trimmed.
- Content is required and trimmed.
- Category and priority must be from allowed fixed values.
- Empty or whitespace-only submissions are rejected with a clear flash message.
- Reasonable server-side length limits should be enforced, for example 120 characters for title and 2000 characters for content.

The page should reuse the existing main-site visual language:

- Existing `static/css/style.css`.
- Existing Bootstrap and Bootstrap Icons.
- Existing logo asset.
- Existing `static/js/i18n.js`.
- Existing `langToggleBtn` behavior.

The main site's current visual theme should remain unchanged.

## Admin Review UI

The administrator module appears inside the main authenticated layout.

Main elements:

- Page header: "System Optimization Suggestions".
- Record count.
- Search input using the existing table filter behavior where practical.
- Table columns:
  - ID.
  - Title.
  - Category.
  - Priority.
  - Status.
  - Submitter.
  - Role.
  - Submitted date.
  - Actions or status update control.
- Detail display for suggestion content, either inline in the table, in a modal, or in an expanded detail section.

Recommended behavior:

- Default sort newest first.
- Status badges use existing badge styling.
- Status updates are optional but useful; if included, they should update `status`, `admin_notes` if present, and `updated_at`.

Only administrators can access this module or see its sidebar link.

## Data Flow

1. User opens `/suggestions`.
2. If not authenticated, Flask-Login redirects to `/login?next=/suggestions`.
3. Authenticated user submits title, category, priority, and content.
4. Backend validates fixed values and required text.
5. Backend inserts a row with current user's ID, username snapshot, role snapshot, and timestamps.
6. Administrator opens the main-site admin module.
7. Admin list reads from the same table and shows the submitted record.
8. If implemented, admin status updates write back to the same table.

This keeps the submission page operationally separate while preserving real-time information sharing through one database table.

## Error Handling

Submission errors:

- Missing title or content: flash a warning and keep the user on the form.
- Invalid category or priority: reject the submission server-side.
- Database failure: show a generic failure flash and do not claim success.

Access errors:

- Anonymous visitors follow the existing Flask-Login redirect behavior.
- Non-admin users attempting to access `/admin/suggestions` are redirected by `role_required('admin')` with the existing insufficient-permissions flash.

Status update errors:

- Invalid status values are rejected.
- Missing suggestion IDs return the existing Flask-style not-found behavior or redirect with a warning.

## i18n

Add new user-facing strings to `static/js/i18n.js`.

Expected keys include:

- `System Optimization Suggestions`
- `Submit Suggestion`
- `Suggestion Title`
- `Suggestion Details`
- `Category`
- `Priority`
- `Submitted By`
- `Submitted Date`
- `Admin Notes`
- `Functionality`
- `Usability`
- `Performance`
- `Data Quality`
- `Security`
- `Reporting`
- `Other`
- `Low`
- `Medium`
- `High`
- `Urgent`
- `New`
- `Reviewed`
- `Planned`
- `Resolved`
- `Suggestion submitted successfully`
- `Please enter a suggestion title`
- `Please enter suggestion details`

Avoid rewriting the existing i18n file broadly because some Chinese output appears garbled in PowerShell due to encoding display. Add only the new keys required for this feature.

## Testing

Add focused tests in the existing `unittest` style.

Backend and route tests:

- The table creation helper creates `system_optimization_suggestions`.
- Anonymous `GET /suggestions` redirects to login.
- Authenticated viewer can load `/suggestions`.
- Authenticated finance and event coordinator users can submit suggestions.
- Submitted suggestions persist with submitter ID, username snapshot, role snapshot, title, category, priority, content, status, and timestamps.
- Invalid category or priority is rejected.
- Empty title or content is rejected.
- Non-admin users cannot access `/admin/suggestions`.
- Admin users can access `/admin/suggestions` and see submitted suggestions.
- Admin status update accepts allowed statuses and rejects invalid statuses, if status updates are implemented.

Template and i18n tests:

- Submission template includes the shared stylesheet and `i18n.js`.
- Submission template includes `langToggleBtn` or an equivalent hook used by `I18n.updateToggleBtn()`.
- Admin sidebar link is under Administration and guarded by `current_user.is_admin`.
- New user-facing labels use `data-i18n` or related i18n attributes.
- `static/js/i18n.js` includes the new keys.

Run targeted tests first, then `python -m unittest discover` before completing implementation if feasible.

## Risks

The main risk is blurring the boundary between an independent submission surface and the authenticated main module shell. The design keeps `/suggestions` as a separate page while still using the same auth session, CSS, logo, and language tooling.

Another risk is accidentally allowing anonymous submission because the original requirement allowed it. The final requirement is login required for submission by any account.

The existing worktree already contains unrelated modifications. Implementation should avoid reverting or staging unrelated files and should treat any existing `elder_care.db` changes carefully.
