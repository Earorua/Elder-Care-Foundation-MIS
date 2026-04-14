# AI Agent Recent History Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent recent-question sidebar to the AI Agent page for the last ten successful questions.

**Architecture:** Keep the feature in the existing Jinja template because the Agent API already returns the question, answer, SQL, columns, and rows needed for recall. Store records in browser `localStorage` under a dedicated key, render them in a new right-side panel, and reuse the existing answer/SQL/table render functions when a history entry is clicked.

**Tech Stack:** Flask/Jinja2 template, browser JavaScript, Bootstrap-compatible HTML/CSS, existing `I18n` helper, Python `unittest` template checks.

---

### Task 1: Failing Template Tests

**Files:**
- Modify: `tests/test_agent_helpers.py`

- [ ] **Step 1: Add failing tests for history UI hooks and persistence helpers**

Add tests to `AgentHelperTests` that read `templates/agent/index.html` and assert the following strings exist:

```python
def test_agent_recent_history_panel_hooks_exist(self):
    template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

    for hook in [
        "agent-history-list",
        "agentHistoryList",
        "agentHistoryEmpty",
        "Recent Questions",
        "No recent questions yet.",
        "data-history-index",
    ]:
        with self.subTest(hook=hook):
            self.assertIn(hook, template)

def test_agent_recent_history_uses_local_storage_and_limits_to_ten(self):
    template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

    for hook in [
        "AGENT_HISTORY_KEY",
        "localStorage.getItem(AGENT_HISTORY_KEY)",
        "localStorage.setItem(AGENT_HISTORY_KEY",
        "historyEntries.slice(0, 10)",
        "saveHistoryEntry({",
        "renderHistory()",
        "showHistoryEntry(index)",
    ]:
        with self.subTest(hook=hook):
            self.assertIn(hook, template)
```

- [ ] **Step 2: Add failing i18n test expectations**

Extend `test_agent_page_has_i18n_entries_and_dynamic_status_translation` so the expected keys include:

```python
"Recent Questions",
"No recent questions yet.",
"Saved questions appear here after the Agent returns an answer.",
"Saved",
```

- [ ] **Step 3: Run tests to verify failure**

Run: `python -m unittest tests.test_agent_helpers`

Expected: FAIL because the history panel and new i18n keys are not implemented yet.

### Task 2: Agent Template Implementation

**Files:**
- Modify: `templates/agent/index.html`
- Modify: `static/js/i18n.js`

- [ ] **Step 1: Add the history panel markup**

Add a new `agent-panel agent-side-section` inside the existing `<aside class="agent-side">` with:

```html
<section class="agent-panel agent-side-section">
  <h5><i class="bi bi-clock-history me-1"></i><span data-i18n="Recent Questions">Recent Questions</span></h5>
  <div class="agent-history-empty" id="agentHistoryEmpty">
    <div data-i18n="No recent questions yet.">No recent questions yet.</div>
    <small data-i18n="Saved questions appear here after the Agent returns an answer.">Saved questions appear here after the Agent returns an answer.</small>
  </div>
  <div class="agent-history-list" id="agentHistoryList"></div>
</section>
```

- [ ] **Step 2: Add scoped CSS for the history panel**

Add styles for `.agent-history-empty`, `.agent-history-list`, `.agent-history-item`, `.agent-history-question`, and `.agent-history-meta` using the existing warm borders and 8px radius.

- [ ] **Step 3: Add JavaScript history helpers**

Inside the existing IIFE, add constants and helpers:

```javascript
const historyList = document.getElementById('agentHistoryList');
const historyEmpty = document.getElementById('agentHistoryEmpty');
const AGENT_HISTORY_KEY = 'ecmis_agent_recent_questions';
let historyEntries = loadHistory();
```

Implement `loadHistory`, `persistHistory`, `renderHistory`, `saveHistoryEntry`, `showHistoryEntry`, `formatHistoryTime`, and `truncateText`. `saveHistoryEntry` deduplicates by `question` and `sql`, writes newest-first, and caps with `historyEntries.slice(0, 10)`.

- [ ] **Step 4: Reuse existing rendering for history click**

When a history item is clicked, populate `question.value`, hide the empty state, show `answerText`, set `answerText.textContent`, set `sqlTrace.textContent`, and call `renderRows(entry.columns || [], entry.rows || [])`.

- [ ] **Step 5: Save successful responses**

After a successful fetch response and after rendering the answer/table, call:

```javascript
saveHistoryEntry({
  question: text,
  answer: data.answer || I18n.t('No answer returned.'),
  sql: data.sql || I18n.t('No SQL returned.'),
  columns: data.columns || [],
  rows: data.rows || [],
  totalRows: data.total_rows || 0,
  savedAt: new Date().toISOString()
});
```

- [ ] **Step 6: Add i18n keys**

Add the four new English keys to the AI Agent section of `static/js/i18n.js`.

### Task 3: Verification

**Files:**
- No new files.

- [ ] **Step 1: Run the targeted Agent tests**

Run: `python -m unittest tests.test_agent_helpers`

Expected: PASS.

- [ ] **Step 2: Run the broader existing targeted tests**

Run: `python -m unittest tests.test_agent_helpers tests.test_bi_ui_template`

Expected: PASS.

- [ ] **Step 3: Inspect git diff**

Run: `git diff -- templates/agent/index.html static/js/i18n.js tests/test_agent_helpers.py docs/superpowers/specs/2026-04-14-agent-recent-history-sidebar-design.md docs/superpowers/plans/2026-04-14-agent-recent-history-sidebar.md`

Expected: Diff only contains the history sidebar feature, new tests, and the related docs.
