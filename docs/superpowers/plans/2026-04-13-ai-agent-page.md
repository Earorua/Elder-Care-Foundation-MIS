# AI Agent Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone AI Agent page that answers natural-language questions about the full SQLite database through SiliconFlow `Qwen/Qwen3.5-4B`.

**Architecture:** Add a new Flask blueprint with small testable helpers for schema extraction, model calls, SQL validation, and row formatting. The page posts a question to `/api/agent/query`, the backend asks SiliconFlow for read-only SQL, executes it against SQLite, then asks SiliconFlow to summarize the results.

**Tech Stack:** Flask, Jinja2, sqlite3, urllib from the Python standard library, Bootstrap 5, existing project CSS variables, Python `unittest`.

---

### Task 1: Backend Helper Tests

**Files:**
- Create: `tests/test_agent_helpers.py`
- Create: `blueprints/agent.py`

- [ ] **Step 1: Write failing tests for SQL safety and limits**

```python
import unittest

from blueprints.agent import _ensure_limit, _validate_readonly_sql


class AgentHelperTests(unittest.TestCase):
    def test_validate_readonly_sql_accepts_select_and_with(self):
        self.assertEqual(_validate_readonly_sql("SELECT * FROM donors"), "SELECT * FROM donors")
        self.assertEqual(
            _validate_readonly_sql("WITH recent AS (SELECT * FROM donations) SELECT * FROM recent"),
            "WITH recent AS (SELECT * FROM donations) SELECT * FROM recent",
        )

    def test_validate_readonly_sql_rejects_mutation_and_multiple_statements(self):
        for sql in [
            "DELETE FROM donors",
            "SELECT * FROM donors; DROP TABLE donors",
            "UPDATE donors SET age = 1",
            "PRAGMA table_info(donors)",
        ]:
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):
                    _validate_readonly_sql(sql)

    def test_ensure_limit_adds_default_limit_and_preserves_existing_limit(self):
        self.assertEqual(_ensure_limit("SELECT * FROM donors", 200), "SELECT * FROM donors LIMIT 200")
        self.assertEqual(_ensure_limit("SELECT * FROM donors LIMIT 5", 200), "SELECT * FROM donors LIMIT 5")
        self.assertEqual(
            _ensure_limit("WITH x AS (SELECT * FROM donors) SELECT * FROM x", 200),
            "WITH x AS (SELECT * FROM donors) SELECT * FROM x LIMIT 200",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run helper tests to verify they fail**

Run: `python -m unittest tests.test_agent_helpers`

Expected: FAIL because `blueprints.agent` or helper functions do not exist yet.

- [ ] **Step 3: Add minimal helper implementation**

Create `blueprints/agent.py` with helper functions only: `_strip_sql_fences`, `_validate_readonly_sql`, and `_ensure_limit`.

- [ ] **Step 4: Run helper tests to verify they pass**

Run: `python -m unittest tests.test_agent_helpers`

Expected: PASS.

### Task 2: Schema and Endpoint Setup Tests

**Files:**
- Modify: `tests/test_agent_helpers.py`
- Modify: `blueprints/agent.py`

- [ ] **Step 1: Write failing tests for schema extraction and missing API key**

Add tests that build a temporary Flask app with an in-memory database, assert `_get_database_schema()` includes a table and column, and assert `/api/agent/query` returns a clear setup error when `SILICONFLOW_API_KEY` is empty.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_agent_helpers`

Expected: FAIL because schema extraction and the endpoint do not exist yet.

- [ ] **Step 3: Implement schema extraction and missing-key endpoint path**

Add `agent_bp`, `agent_index`, `agent_query`, `_get_database_schema`, and missing-key validation.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_agent_helpers`

Expected: PASS.

### Task 3: SiliconFlow Query Flow

**Files:**
- Modify: `blueprints/agent.py`
- Modify: `config.py`

- [ ] **Step 1: Write failing tests for request payload parsing**

Add tests for extracting JSON SQL from a model response and for formatting SQLite rows into JSON-safe dictionaries.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_agent_helpers`

Expected: FAIL because extraction and row formatting helpers do not exist.

- [ ] **Step 3: Implement SiliconFlow helpers**

Add `_call_siliconflow`, `_extract_json_object`, `_build_sql_prompt`, `_build_answer_prompt`, and `_rows_to_dicts`. Add `SILICONFLOW_API_KEY`, `SILICONFLOW_BASE_URL`, `SILICONFLOW_MODEL`, and `AGENT_ROW_LIMIT` to `config.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_agent_helpers`

Expected: PASS.

### Task 4: Page, Navigation, and Styling

**Files:**
- Create: `templates/agent/index.html`
- Modify: `templates/base.html`
- Modify: `app.py`
- Modify: `static/js/i18n.js`

- [ ] **Step 1: Write failing template/registration tests**

Add tests that check `templates/agent/index.html` contains the workspace hooks, `templates/base.html` links to `agent.agent_index`, and `app.py` registers `agent_bp`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_agent_helpers`

Expected: FAIL because the template and registration are missing.

- [ ] **Step 3: Implement UI and registration**

Create the Jinja template with chat form, starter prompts, SQL trace, and result preview. Register the blueprint in `app.py`, add the sidebar link under Analytics, and add any new i18n keys.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_agent_helpers`

Expected: PASS.

### Task 5: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run targeted test suite**

Run: `python -m unittest tests.test_agent_helpers tests.test_bi_ui_template`

Expected: PASS.

- [ ] **Step 2: Run Flask import smoke test**

Run: `python -c "from app import create_app; app = create_app(); print('ok', 'agent.agent_index' in [str(r.endpoint) for r in app.url_map.iter_rules()])"`

Expected: `ok True`.

- [ ] **Step 3: Report API key location**

Tell the user to paste the SiliconFlow key into `config.py`:

```python
SILICONFLOW_API_KEY = 'paste-your-key-here'
```
