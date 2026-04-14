# Table Fixed Value i18n Design

## Goal

Make fixed option values displayed inside management-page table cells switch between English and Chinese with the existing language toggle.

Examples include gender, person type, role, status, donation method, payment type, event type, gift type, batch type, feedback status, delivery status, and boolean values such as Yes/No or Active/Inactive.

The database should continue storing canonical values. This change only affects display text in table cells.

## Scope

In scope:

- CRUD and report table cells that display fixed values from database fields.
- Boolean table values rendered as Yes/No, Active/Inactive, Present/Absent, Free/Donor Gift, or similar fixed labels.
- Existing management templates under `templates/auth`, `templates/donations`, `templates/personnel`, `templates/gifts`, `templates/events`, and `templates/finance`.
- Existing `static/js/i18n.js` translations and `I18n.applyAll()` behavior.

Out of scope:

- Free-text database values such as names, descriptions, notes, emails, addresses, locations, gift names, event names, supplier names, and donor names.
- IDs, dates, amounts, counts, and calculated numeric values.
- BI Explorer result rows and charts.
- Dashboard chart labels.
- AI Agent returned SQL result rows and natural-language answers.
- Changing database values or form submission values.

## Design

Add a small Jinja macro file, for example `templates/macros/i18n_values.html`, with focused helpers for table-cell values:

```jinja2
{% macro value(text) -%}
  {% if text is not none and text|string %}
    <span data-i18n="{{ text }}">{{ text }}</span>
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

For values that need normalized display keys, keep the stored value unchanged and only pass the display key to the macro. Example:

```jinja2
<td>{{ i18n_value("Active" if r.is_active else "Inactive") }}</td>
```

This reuses the existing frontend translation pass:

- `I18n.applyAll()` already translates all elements with `data-i18n`.
- Form option values that already use `data-i18n` keep working.
- Table values become consistent with form options and headings.

## Target Fields

Initial coverage should include these table-cell fields where present:

- Donations: `donation_type`, `is_tax_deductible`.
- Donors: `gender`, `marital_status`.
- Donation categories: `is_active`.
- Feedback and receipts: `donation_type`, `feedback_type`, `status`.
- Personnel: `person_type`, `role_name`, `gender`, `marital_status`, `status`.
- Payments: `payment_type`.
- Schedules and schedule board table-like sections: `schedule_type`, `status`, absence/attendance labels.
- Events: `event_type`, `status`.
- Gifts: `gift_type`, `is_active`.
- Gift batches: `batch_type`.
- Gift distribution: `is_free`, `distribution_reason` when the value comes from the fixed dropdown list.
- Delivery: `delivery_status`.
- Finance reports: grouped `donation_type`, `income_type`, `payment_type`, and fixed source labels.
- Auth users: `role`, active/inactive status.

## Translation Keys

Most keys already exist in `static/js/i18n.js`. Add missing keys for fixed values found in current sample data and forms.

Translation keys should remain the canonical English display strings. Do not add generated keys or database-specific prefixes unless a real collision appears. Current collisions such as `Active` and `Status` are acceptable because they already represent common UI words.

## Tests

Add focused template/i18n tests:

- The macro file exists and renders `data-i18n`.
- Key templates import the macro.
- Table cells for representative fixed values are wrapped with `i18n_value(...)`.
- `static/js/i18n.js` contains expected keys such as `Male`, `Female`, `Employee`, `Volunteer`, `Cash`, `Check`, `Wire Transfer`, `Salary`, `Bonus`, `Active`, `Inactive`, `planned`, `completed`, `delivered`, and `in_transit`.

Existing tests for marital status and BI templates should continue to pass.

## Risks

Some database values are not true fixed options even if their column name looks categorical. Avoid translating values that are user-entered or entity names.

Wrapping table values with spans may affect table search only if search code depends on raw text structure. The existing search checks row text, so translated text remains searchable in the active language.

Some existing Chinese translations in `i18n.js` appear garbled in PowerShell output due to encoding display. Do not rewrite the whole file. Add only the missing keys needed for this change.
