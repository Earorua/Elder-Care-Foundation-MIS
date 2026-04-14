# AI Agent Semantic Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve AI Agent SQL generation accuracy for business synonyms such as `staff member` by adding richer semantic context and stronger enum-filter repair.

**Architecture:** Keep the current free-form read-only SQL Agent flow. Add deterministic prompt context helpers in `blueprints/agent.py`, import compact metadata constants from `blueprints.bi`, and extend semantic repair so entity synonyms are not treated as literal enum values.

**Tech Stack:** Flask, SQLite, Python `unittest`, existing SiliconFlow chat-completions integration.

---

## File Structure

- Modify: `blueprints/agent.py`
  - Add business concept alias context.
  - Add compact BI metadata context sourced from `blueprints.bi`.
  - Add entity-synonym misuse detection for enum filters.
  - Include detected semantic issues in the existing semantic repair prompt path.
- Modify: `tests/test_agent_helpers.py`
  - Add tests for schema context and synonym repair behavior.
  - Keep existing mocked SiliconFlow endpoint tests.

---

### Task 1: Add Failing Tests for Semantic Context

**Files:**
- Modify: `tests/test_agent_helpers.py`

- [ ] **Step 1: Write failing schema-context tests**

Add the following test methods inside `AgentHelperTests`, near the existing schema tests:

```python
    def test_get_database_schema_includes_business_concept_aliases(self):
        app, db_path = self._make_temp_app()
        try:
            with app.app_context():
                schema = _get_database_schema()
        finally:
            os.unlink(db_path)

        self.assertIn("Business concept aliases", schema)
        self.assertIn("staff member/staff/personnel -> persons records", schema)
        self.assertIn("employee -> persons.person_type = Employee", schema)
        self.assertIn("volunteer -> persons.person_type = Volunteer", schema)

    def test_get_database_schema_includes_compact_bi_metadata_context(self):
        app, db_path = self._make_temp_app()
        try:
            with app.app_context():
                schema = _get_database_schema()
        finally:
            os.unlink(db_path)

        self.assertIn("BI metadata context", schema)
        self.assertIn("Domains: donor, person, event, gift, finance, schedule", schema)
        self.assertIn("Filter donor_age: Donor Age -> dn.age", schema)
        self.assertIn("Metric total_donation: Total Donation Amount -> SUM(d.amount)", schema)
        self.assertIn("Domain person base: FROM persons p LEFT JOIN payments pay ON p.person_id = pay.person_id", schema)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.test_agent_helpers
```

Expected: FAIL because the schema context does not yet include `Business concept aliases` or `BI metadata context`.

---

### Task 2: Implement Semantic Context Helpers

**Files:**
- Modify: `blueprints/agent.py`

- [ ] **Step 1: Import BI metadata constants**

Add this import after the existing auth import:

```python
from blueprints.bi import (
    DIMENSION_DEFS,
    DOMAIN_BASES,
    FILTER_DEFS,
    METRIC_DEFS,
    VALID_DOMAINS,
)
```

- [ ] **Step 2: Include new context in `_get_database_schema`**

Change the end of `_get_database_schema()` to:

```python
    parts.append("")
    parts.append(_get_business_semantic_context())
    parts.append("")
    parts.append(_get_business_concept_alias_context())
    parts.append("")
    parts.append(_get_bi_metadata_context())
    parts.append("")
    parts.append(_format_enum_value_context(_get_enum_values_by_column(db)))
    return "\n".join(parts)
```

- [ ] **Step 3: Add `_get_business_concept_alias_context`**

Add this helper after `_get_business_semantic_context()`:

```python
def _get_business_concept_alias_context():
    return "\n".join(
        [
            "Business concept aliases:",
            "- staff member/staff/personnel -> persons records, not persons.person_type = Staff.",
            "- team member/worker -> persons records unless the user explicitly asks for a narrower category.",
            "- employee -> persons.person_type = Employee.",
            "- volunteer -> persons.person_type = Volunteer.",
            "- donor/contributor/supporter -> donors records.",
            "- gift/inventory/stock -> gifts records; stock questions use gifts.current_stock and gifts.min_stock_level.",
            "- income/revenue/funding -> grants plus other_income for finance income questions.",
        ]
    )
```

- [ ] **Step 4: Add BI metadata formatting helpers**

Add these helpers after `_get_business_concept_alias_context()`:

```python
def _get_bi_metadata_context():
    lines = [
        "BI metadata context:",
        f"Domains: {', '.join(VALID_DOMAINS)}",
    ]
    lines.extend(_format_bi_definitions("Filter", FILTER_DEFS))
    lines.extend(_format_bi_definitions("Dimension", DIMENSION_DEFS))
    lines.extend(_format_bi_definitions("Metric", METRIC_DEFS))
    for domain in VALID_DOMAINS:
        base_sql = " ".join(DOMAIN_BASES[domain].split())
        lines.append(f"Domain {domain} base: {base_sql}")
    return "\n".join(lines)


def _format_bi_definitions(kind, definitions):
    lines = []
    for key, definition in definitions.items():
        sql = definition.get("sql")
        label = definition.get("label")
        if sql and label:
            lines.append(f"{kind} {key}: {label} -> {sql}")
    return lines
```

- [ ] **Step 5: Run tests to verify Task 1 passes**

Run:

```bash
python -m unittest tests.test_agent_helpers
```

Expected: PASS for the new schema-context tests; other existing tests should remain green.

---

### Task 3: Add Failing Tests for Entity-Synonym Misuse Repair

**Files:**
- Modify: `tests/test_agent_helpers.py`

- [ ] **Step 1: Write failing direct helper test**

Update `test_find_unknown_enum_filters_flags_invalid_aliased_enum_value` so `staff` is treated as an entity-synonym misuse, then add this test near it for `personnel`:

```python
    def test_find_unknown_enum_filters_flags_invalid_aliased_enum_value(self):
        enum_values = {"persons.person_type": ["Employee", "Volunteer"]}
        self.assertTrue(hasattr(agent_module, "_find_unknown_enum_filters"))

        issues = agent_module._find_unknown_enum_filters(
            "SELECT COUNT(*) FROM persons p "
            "JOIN donors d ON LOWER(p.email) = LOWER(d.email) "
            "WHERE LOWER(p.person_type) = 'staff'",
            enum_values,
        )

        self.assertEqual(
            issues,
            [
                "persons.person_type uses entity synonym 'staff'; "
                "interpret it as persons records instead of an enum filter"
            ],
        )
        self.assertEqual(
            agent_module._find_unknown_enum_filters(
                "SELECT COUNT(*) FROM persons p WHERE LOWER(p.person_type) = 'employee'",
                enum_values,
            ),
            [],
        )

    def test_find_unknown_enum_filters_flags_entity_synonym_enum_misuse(self):
        enum_values = {"persons.person_type": ["Employee", "Volunteer"]}

        issues = agent_module._find_unknown_enum_filters(
            "SELECT COUNT(*) FROM persons p WHERE LOWER(p.person_type) = 'personnel'",
            enum_values,
        )

        self.assertEqual(
            issues,
            [
                "persons.person_type uses entity synonym 'personnel'; "
                "interpret it as persons records instead of an enum filter"
            ],
        )
```

- [ ] **Step 2: Write endpoint repair test for `personnel`**

Update the existing `test_agent_query_repairs_generated_sql_with_unknown_enum_value` repair prompt assertion so it expects the `staff` entity-synonym issue:

```python
        self.assertIn("entity synonym 'staff'", repair_prompt)
        self.assertIn("interpret it as persons records", repair_prompt)
```

Then add this test near it for `personnel`:

```python
    def test_agent_query_repairs_personnel_entity_synonym_enum_filter(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["SILICONFLOW_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_siliconflow",
                side_effect=[
                    json.dumps(
                        {
                            "sql": (
                                "SELECT COUNT(*) AS count "
                                "FROM persons p WHERE LOWER(p.person_type) = 'personnel'"
                            ),
                            "rationale": "Count personnel.",
                        }
                    ),
                    json.dumps(
                        {
                            "sql": "SELECT COUNT(*) AS count FROM persons p",
                            "rationale": "Treat personnel as all person records.",
                        }
                    ),
                    "There are 2 personnel records.",
                ],
            ) as mock_call:
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "How many personnel records are there?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_call.call_count, 3)
        self.assertNotIn("person_type", payload["sql"])
        self.assertEqual(payload["rows"], [{"count": 2}])
        repair_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("entity synonym 'personnel'", repair_prompt)
        self.assertIn("interpret it as persons records", repair_prompt)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.test_agent_helpers
```

Expected: FAIL because `_find_unknown_enum_filters()` does not yet distinguish entity-synonym enum misuse.

---

### Task 4: Implement Entity-Synonym Misuse Detection

**Files:**
- Modify: `blueprints/agent.py`

- [ ] **Step 1: Add entity-synonym constants**

Add these constants near `MAX_ENUM_CONTEXT_VALUES`:

```python
ENTITY_SYNONYMS_BY_COLUMN = {
    "persons.person_type": {
        "staff",
        "staff member",
        "staff members",
        "personnel",
        "team member",
        "team members",
        "worker",
        "workers",
    },
}
```

- [ ] **Step 2: Update `_find_unknown_enum_filters`**

Replace the inner `used_value` handling with:

```python
            for used_value in used_values:
                entity_issue = _entity_synonym_enum_issue(column_key, used_value)
                if entity_issue:
                    issue = entity_issue
                elif _is_known_enum_value(used_value, valid_values):
                    continue
                else:
                    issue = (
                        f"{table_name}.{column_name} uses unsupported value "
                        f"'{used_value}'; valid values are {', '.join(valid_values)}"
                    )
                if issue not in seen:
                    seen.add(issue)
                    issues.append(issue)
```

- [ ] **Step 3: Add `_entity_synonym_enum_issue` helper**

Add this helper before `_is_known_enum_value()`:

```python
def _entity_synonym_enum_issue(column_key, value):
    normalized = value.strip().lower()
    synonyms = ENTITY_SYNONYMS_BY_COLUMN.get(column_key, set())
    if normalized not in synonyms:
        return ""
    if column_key == "persons.person_type":
        return (
            f"{column_key} uses entity synonym '{value}'; "
            "interpret it as persons records instead of an enum filter"
        )
    return (
        f"{column_key} uses entity synonym '{value}'; "
        "interpret it as the documented business entity instead of an enum filter"
    )
```

- [ ] **Step 4: Strengthen semantic repair prompt wording**

In `_build_sql_semantic_repair_prompt()`, change the first sentence to:

```python
        "The previous SQL used unsupported enum values or treated business entity synonyms as enum values for this database.\n"
```

Keep the existing sentence:

```python
        "If the user used a documented business synonym, map it to the documented table or valid enum values. "
```

- [ ] **Step 5: Run tests to verify Task 3 passes**

Run:

```bash
python -m unittest tests.test_agent_helpers
```

Expected: PASS for the new synonym misuse tests and existing Agent tests.

---

### Task 5: Full Verification and Commit

**Files:**
- Verify: `blueprints/agent.py`
- Verify: `tests/test_agent_helpers.py`

- [ ] **Step 1: Run focused suite**

Run:

```bash
python -m unittest tests.test_agent_helpers tests.test_bi_ui_template tests.test_marital_status_ui
```

Expected: all tests pass.

- [ ] **Step 2: Inspect diff**

Run:

```bash
git diff -- blueprints/agent.py tests/test_agent_helpers.py
git status --short
```

Expected: only `blueprints/agent.py`, `tests/test_agent_helpers.py`, and this plan file are modified in the implementation worktree.

- [ ] **Step 3: Commit implementation**

Run:

```bash
git add blueprints/agent.py tests/test_agent_helpers.py docs/superpowers/plans/2026-04-14-ai-agent-semantic-mapping.md
git commit -m "feat: improve AI Agent semantic mapping"
```

Expected: commit succeeds on branch `agent-semantic-mapping`.
