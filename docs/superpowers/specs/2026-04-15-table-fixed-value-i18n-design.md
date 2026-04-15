# Table Fixed Value i18n Design

## Goal

Make fixed option values displayed inside front-end table cells switch between English and Chinese with the existing language toggle.

This includes values such as gender, type, role, status, donation method, payment type, event type, gift type, batch type, delivery status, feedback status, and boolean labels such as Yes/No or Active/Inactive.

The database must continue storing the same canonical values. This change only affects display text.

## Scope

In scope:

- Server-rendered CRUD and report table cells that display fixed values from database fields.
- Client-rendered table-like sections, especially Schedule Board cards and daily attendance tables.
- Fixed values inside mixed table-cell text, such as `#12 (Physical)` or `Salary (4 payments)`.
- Boolean table values rendered as Yes/No, Active/Inactive, Present/Absent, Free/Donor Gift, or similar fixed labels.
- Existing templates under `templates/auth`, `templates/donations`, `templates/personnel`, `templates/gifts`, `templates/events`, and `templates/finance`.
- Existing `static/js/i18n.js` translations and `I18n.applyAll()` behavior.

Out of scope:

- Free-text database values such as names, descriptions, notes, emails, addresses, locations, gift names, event names, supplier names, donor names, feedback text, and source names.
- IDs, dates, amounts, counts, and calculated numeric values.
- BI Explorer result rows and charts.
- Dashboard chart labels.
- AI Agent returned SQL result rows and natural-language answers.
- Changing database values or form submission values.

## Core Rules

1. Store canonical values, translate display text only.
2. Translate only values known to be fixed options.
3. Normalize internal values to display keys before translation.
4. Wrap or translate only the fixed-value fragment inside mixed text.
5. Cover both server-rendered HTML and client-rendered HTML.

Examples:

- `Male` can be translated directly.
- `event_coordinator` should display through a normalized key such as `Event Coordinator`.
- `in_transit` should display through a normalized key such as `In Transit`.
- `#12 (Physical)` should translate only `Physical`, not the whole string.
- `Bank of America` should not be translated because it is a source/entity name.

## Server-Rendered Table Design

Add a small Jinja macro file, for example `templates/macros/i18n_values.html`, with focused helpers for table-cell fixed values:

```jinja2
{% macro value(key) -%}
  {% if key is not none and key|string %}
    <span data-i18n="{{ key }}">{{ key }}</span>
  {% endif %}
{%- endmacro %}
```

Templates will import the macro and wrap fixed values:

```jinja2
{% from "macros/i18n_values.html" import value as i18n_value %}

<td>{{ i18n_value(d.gender) }}</td>
<td>{{ i18n_value(d.donation_type) }}</td>
<td>{{ i18n_value("Yes" if d.is_tax_deductible else "No") }}</td>
```

For values that need normalized display keys, keep the stored value unchanged and only pass the display key to the macro:

```jinja2
<td>{{ i18n_value("Active" if r.is_active else "Inactive") }}</td>
<td>{{ i18n_value("Event Coordinator" if u.role == "event_coordinator" else "Finance") }}</td>
```

Mixed cells must wrap only the fixed fragment:

```jinja2
<td>#{{ r.batch_id }} ({{ i18n_value(r.batch_type) }})</td>
<td>{{ i18n_value(r.payment_type) }} <small>({{ r.cnt }} <span data-i18n="payments">payments</span>)</small></td>
```

Do not wrap free-text values, even when they appear in the same table.

## Client-Rendered Table Design

Jinja macros do not cover table HTML assembled in JavaScript. Add a small frontend helper in `static/js/i18n.js`, for example:

```javascript
function value(key) {
  const normalized = VALUE_KEY_MAP[key] || key;
  return t(normalized);
}
```

Expose it as `I18n.value(...)` next to `I18n.t(...)`.

Use this helper in client-rendered table-like areas, especially:

- Schedule Board cards: `role_name`, `schedule_type`, attendance/status badges.
- Schedule Board daily attendance table: role and attendance cells.
- Event status badge in Schedule Board metadata.

JavaScript-generated HTML should not rely on `data-i18n` unless `I18n.applyAll()` is called after insertion. For direct template strings, prefer `I18n.value(...)` or `I18n.t(...)` at render time.

## Normalization

Some stored values are not good translation keys. The implementation should normalize these before display:

- Auth roles:
  - `admin` -> `Admin`
  - `finance` -> `Finance`
  - `event_coordinator` -> `Event Coordinator`
  - `viewer` -> `Viewer`
- Lowercase or snake-case status values:
  - `active` -> `active` for personnel employment status
  - `inactive` -> `inactive` for personnel employment status
  - `planned` -> `Planned`
  - `completed` -> `Completed`
  - `scheduled` -> `Scheduled`
  - `in_progress` -> `In Progress`
  - `absent` -> `Absent`
  - `cancelled` -> `Cancelled`
  - `delivered` -> `Delivered`
  - `in_transit` -> `In Transit`
  - `pending` -> `Pending`
  - `resolved` -> `Resolved`
  - `reviewed` -> `Reviewed`

Avoid translating all values by column name alone. A column such as `source_name`, `description`, or `distribution_reason` can contain user-entered or entity-specific text.

## Semantic Collisions

Some English keys are shared across different contexts. Use shared keys only when the Chinese display text is genuinely the same.

Recommended handling:

- Account/gift/category enabled state can use `Active` and `Inactive`.
- Personnel employment status should use lowercase `active` and `inactive`, because the Chinese text should mean employed/left rather than enabled/disabled.
- Event lifecycle should use `Planned`, `Completed`, `Cancelled`, and `Active` only where the meaning is an event state.
- If a collision appears during implementation, add a clearer display key such as `Event Active` or `Account Active` instead of reusing a misleading generic key.

Do not add duplicate keys to `static/js/i18n.js`; JavaScript object literals keep only the last duplicate value. Consolidate or add context-specific keys instead.

## Target Fields

Initial coverage should include these table-cell fields where present:

- Donations: `donation_type`, `is_tax_deductible`.
- Donors: `gender`, `marital_status`.
- Donation categories: `is_active`.
- Feedback and receipts: `donation_type`, `feedback_type`, `status`.
- Personnel persons: `person_type`, `role_name`, `gender`, `marital_status`, `status`.
- Personnel payments: `payment_type`.
- Personnel schedules: `schedule_type`, `status`, absence/attendance labels.
- Schedule Board: `role_name`, `schedule_type`, event status badge, attendance labels, daily attendance table role/status cells.
- Events: `event_type`, `status`.
- Gifts: `gift_type`, `is_active`.
- Gift batches: `batch_type`.
- Gift distribution: `batch_type` inside batch labels, `is_free`, and `distribution_reason` only when the value is from the fixed dropdown list.
- Delivery: `delivery_status`.
- Finance reports: grouped `donation_type`, `income_type`, and `payment_type`.
- Auth users: `role`, active/inactive status.

## Current Sample Values To Cover

The current database and forms include these fixed values:

- Gender: `Male`, `Female`, `Other`.
- Marital status: `Unknown`, `Single`, `Married`, `Divorced`, `Widowed`.
- Person type: `Employee`, `Volunteer`.
- Personnel roles: `Accountant`, `Coordinator`, `Driver`, `Event Helper`, `Gift Packer`, `Manager`, `Receptionist`, `Social Worker`.
- Personnel status: `active`, `inactive`.
- Donation method: `Cash`, `Check`, `Wire Transfer`, `Credit Card`, `In-Kind`.
- Feedback type/status: `Positive`, `Question`, `Suggestion`, `Pending`, `Resolved`, `Reviewed`, `Closed`.
- Payment type: `Salary`, `Bonus`.
- Schedule type/status: `Event`, `Regular`, `Scheduled`, `Completed`, `In Progress`, `Absent`, `Cancelled`.
- Event type/status: `Awareness`, `Fundraiser`, `Gift Collection`, `Walkathon`, `Planned`, `Completed`.
- Gift type/status: `Donor Kit`, `Media`, `Promotional`, `Storybook`, `Active`, `Inactive`.
- Batch type: `Physical`, `Digital`.
- Distribution reason dropdown values: `Donor Thank-You`, `Long-Term Donor Appreciation`, `Major Donor Recognition`, `Corporate Sponsor Gift`, `Event Giveaway`, `Holiday Campaign`, `Community Outreach`, `Promotional Mailing`, `Replacement / Reissue`.
- Delivery status: `Delivered`, `In Transit`.
- Income type: `Fundraising`, `Investment`, `Rental`, `Sales`.
- Auth role: `Admin`, `Finance`, `Event Coordinator`, `Viewer`.
- Boolean labels: `Yes`, `No`, `Present`, `Absent`, `On Time`, `On Duty`.

If current data contains additional fixed values during implementation, add translation keys for them at the same time as the template change.

## Translation Keys

Translation keys should remain canonical English display strings after normalization.

Add missing keys to `static/js/i18n.js` only for values that are actually fixed options. Do not add generated keys, raw IDs, entity names, or free-text values.

When a database stores lowercase or snake-case values, prefer a readable display key unless an existing key intentionally uses lowercase for semantic reasons, such as personnel `active` and `inactive`.

## Tests

Add focused template/i18n tests:

- The macro file exists and renders `data-i18n`.
- Key templates import the macro.
- Representative table cells for fixed values are wrapped with `i18n_value(...)`.
- Mixed cells translate only the fixed-value fragment, not the whole mixed string.
- Auth user roles normalize internal role slugs before display translation.
- Schedule Board JavaScript uses `I18n.value(...)` or equivalent for client-rendered fixed values.
- Target templates no longer contain obvious bare table outputs for covered fields, such as `{{ p['gender'] }}`, `{{ d.donation_type }}`, or `{{ r.delivery_status }}` in table cells.
- `static/js/i18n.js` contains expected keys for sample fixed values, including `Male`, `Female`, `Employee`, `Volunteer`, `Cash`, `Check`, `Wire Transfer`, `Salary`, `Bonus`, `active`, `inactive`, `Planned`, `Completed`, `Scheduled`, `Delivered`, `In Transit`, `Positive`, `Suggestion`, `Reviewed`, `Physical`, and `Digital`.

Existing tests for marital status, BI templates, and agent helpers should continue to pass.

## Risks

Some database values are not true fixed options even if their column name looks categorical. Avoid translating values that are user-entered or entity names.

Wrapping table values with spans may affect table search only if search code depends on raw text structure. The existing search checks row text, so translated text remains searchable in the active language.

Client-rendered content can be missed if implementation only updates Jinja templates. Schedule Board must be handled explicitly.

Some existing Chinese translations in `i18n.js` appear garbled in PowerShell output due to encoding display. Do not rewrite the whole file. Add or consolidate only the keys needed for this change.
