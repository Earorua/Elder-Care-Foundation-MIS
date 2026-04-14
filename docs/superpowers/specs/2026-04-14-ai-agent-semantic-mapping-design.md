# AI Agent Semantic Mapping Design

## Goal

Improve AI Agent natural-language-to-SQL accuracy for business synonyms and near-synonyms, especially cases where a user term names a business entity instead of a literal database enum value. The primary example is `staff member`: it should usually map to the Personnel/persons domain, not to `persons.person_type = 'Staff'`.

The change should reduce incorrect SQL while avoiding frequent clarification prompts. The Agent should answer directly whenever the business meaning is reasonably inferable from the schema and local semantic context.

## Scope

This work updates the Agent backend semantic context and SQL repair path. It does not replace the current read-only SQL execution model, and it does not move the Agent fully to BI Explorer's structured query builder.

In scope:

- Add explicit business concept aliases for common entity and field synonyms.
- Reuse BI Explorer metadata where it helps the model understand user-facing field labels, metrics, domains, and join patterns.
- Extend the generated-SQL semantic repair path so entity synonyms are not preserved as invalid or misleading enum filters.
- Add focused tests for synonym context and semantic repair behavior.

Out of scope:

- A broad clarification-dialog workflow.
- A full model-generated DSL that replaces free-form SQL.
- Database schema migrations or changes to bundled sample data.
- A new frontend conversation UI for follow-up questions.

## Design

The Agent keeps the existing three-stage flow:

1. Build database context.
2. Ask SiliconFlow for a JSON object with `sql` and `rationale`.
3. Validate, optionally repair, execute read-only SQL, and ask the model to summarize rows.

The optimization adds richer context before SQL generation and stronger checks after SQL generation.

### Business Concept Aliases

Add a backend helper that returns concise alias rules for the model. The rules distinguish entity synonyms from enum synonyms:

- `staff member`, `staff`, `personnel`, `team member`, and `worker` usually mean records in `persons`.
- `employee` maps to `persons.person_type = 'Employee'` when the question specifically asks for employees.
- `volunteer` maps to `persons.person_type = 'Volunteer'`.
- `donor`, `contributor`, and `supporter` map to `donors`.
- `gift`, `inventory`, and `stock` map to the `gifts` domain, with `current_stock` and `min_stock_level` used for stock questions.
- `income`, `revenue`, and `funding` map to the finance income view of `grants` plus `other_income`.

Chinese-language aliases can be added in the implementation using UTF-8 source files if they are needed for the Agent prompt. The design keeps this spec ASCII-only to avoid introducing documentation encoding churn.

These aliases are included in the schema context next to the existing business semantic notes and observed enum-like values.

### BI Metadata Context

Add a compact BI metadata summary to the Agent schema context by importing definitions from `blueprints.bi`:

- Domains: donor, person, event, gift, finance, schedule.
- User-facing filter labels and SQL expressions.
- User-facing dimension labels and SQL expressions.
- User-facing metric labels and SQL expressions.
- Domain base join descriptions for paths that are already maintained by BI Explorer.

This context gives the model names users are likely to type, such as `Total Donation Amount`, `Inventory Value`, `Attendance Rate`, and `Person Count`, along with their SQL meaning.

The summary should be compact and deterministic. It should avoid dumping large query option result sets because the Agent already includes observed enum-like values from the live database.

### Semantic Repair

Keep the current unknown-enum repair, then extend it with entity-synonym misuse detection.

If generated SQL filters an enum-like column using a term that is known to mean an entity/domain rather than a database value, the repair prompt should explicitly tell the model that the term must be interpreted as the entity. Example:

```sql
WHERE LOWER(p.person_type) = 'staff'
```

For a question like "How many staff members are also donors?", this should repair to a query over `persons`, joined to `donors` by email, without filtering `person_type = 'Staff'`.

If the user specifically asks for `employee` or `volunteer`, those terms are valid enum-level intents and should map to the corresponding real values when present.

### Clarification Policy

Do not add a normal clarification step in this iteration. The goal is to improve precision without making the Agent ask frequent follow-up questions.

The Agent should still fail closed when SQL is invalid, non-read-only, malformed, or not repairable. A future clarification feature can be added later if a real set of ambiguous production questions proves that asking is necessary.

## Error Handling

Existing error behavior remains:

- Malformed SQL JSON triggers the JSON repair prompt.
- Non-read-only or multi-statement SQL is rejected.
- Unsupported enum values trigger semantic repair.
- Execution errors are returned as request errors.

This design does not add execution-error repair. That can be a separate follow-up because it changes failure handling more broadly than synonym mapping.

## Tests

Add or update tests in `tests/test_agent_helpers.py`:

- Schema context includes a business concept alias section.
- Schema context includes compact BI metadata such as a domain name, a user-facing label, and a metric SQL expression.
- `staff` used as `persons.person_type = 'staff'` is detected as semantic misuse and repaired away from the enum filter.
- `employee` and `volunteer` remain valid person-type intents when they map to observed enum values.
- Existing SQL safety, JSON repair, answer prompt, and row-limit tests continue to pass.

## Risks

Adding more prompt context can increase token use. Keep the BI metadata summary concise and deterministic.

Alias rules can overfit if they are too aggressive. The rules should focus on domain-level terms that are clearly common in this project, with special care to distinguish `staff/personnel` from actual `Employee` and `Volunteer` values.

Importing BI metadata into the Agent introduces a coupling between modules. This is acceptable because the Agent is explicitly using BI as a semantic dictionary, but the import should be limited to constants and helper formatting to avoid invoking BI route logic.
