# BI Balanced Workspace Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the BI Explorer into a more mature, balanced workspace while preserving the current query model, API, and Chart.js behavior.

**Architecture:** Keep the existing two-column BI layout: the left control rail configures the query and the right output workspace presents summary, chart, and table. Most current BI-specific CSS lives inside `templates/bi/index.html`, so this plan refines that scoped style block and only uses `static/css/style.css` for existing global BI button/table polish where it already applies.

**Tech Stack:** Flask/Jinja templates, Bootstrap classes, vanilla JavaScript, Chart.js, CSS media queries, Python `unittest`.

---

## File Structure

- Modify `tests/test_bi_ui_template.py`
  - Add template-level regression tests before editing the UI.
  - Protect the selected workspace structure, chart-before-table ordering, insight strip structure, and mobile/table CSS hooks.
- Modify `templates/bi/index.html`
  - Refine BI-scoped CSS.
  - Add small semantic class hooks to the insight strip, chart card, chart toolbar, and results table wrapper.
  - Keep all query JavaScript and API calls intact.
- Modify `static/css/style.css`
  - Keep the existing BI enhancement selectors.
  - Add narrow global refinements for BI chart type buttons and BI sortable table headers only if needed after the template CSS changes.

## Task 1: Add Regression Tests for the Balanced Workspace Hooks

**Files:**
- Modify: `tests/test_bi_ui_template.py`

- [ ] **Step 1: Add failing tests for the approved structure**

Append these tests inside `class BiUiTemplateTests(unittest.TestCase):`

```python
    def test_bi_balanced_workspace_has_result_layers(self):
        text = _template_text()

        expected_hooks = [
            "bi-insight-strip",
            "bi-insight-item",
            "bi-chart-workspace",
            "bi-chart-toolbar",
            "bi-table-shell",
            "bi-table-scroll",
        ]
        for hook in expected_hooks:
            self.assertIn(hook, text)

        self.assertLess(text.index('id="biInsightPanel"'), text.index('id="biChartWrap"'))
        self.assertLess(text.index('id="biChartWrap"'), text.index('id="biResults"'))

    def test_bi_mobile_and_table_polish_hooks_exist(self):
        text = _template_text()

        expected_css = [
            ".bi-chart-workspace",
            ".bi-chart-toolbar",
            ".bi-table-shell",
            ".bi-table-scroll",
            ".bi-output-workspace",
            "@media (max-width: 767.98px)",
        ]
        for css in expected_css:
            self.assertIn(css, text)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m unittest tests.test_bi_ui_template.BiUiTemplateTests.test_bi_balanced_workspace_has_result_layers tests.test_bi_ui_template.BiUiTemplateTests.test_bi_mobile_and_table_polish_hooks_exist
```

Expected:

```text
FAIL: test_bi_balanced_workspace_has_result_layers
AssertionError: 'bi-insight-strip' not found
```

The second test may also fail on one of the new CSS hooks. If imports fail because `tests/` is not tracked in this workspace, run the file directly instead:

```powershell
python tests\test_bi_ui_template.py
```

## Task 2: Add Workspace Class Hooks and Markup Refinements

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Update the insight panel markup**

Replace:

```html
<div id="biInsightPanel" class="bi-insight-panel rounded p-3 mb-3" style="display:none;">
  <div class="row g-3 align-items-center">
    <div class="col-md-5">
      <div class="bi-insight-kicker" data-i18n="Current question">Current question</div>
      <div id="biInsightQuestion" style="font-weight:700;color:var(--text-primary);"></div>
    </div>
    <div class="col-md-4">
      <div class="bi-insight-kicker" data-i18n="Top result">Top result</div>
      <div id="biInsightTop" class="bi-insight-value"></div>
    </div>
    <div class="col-md-3">
      <div class="bi-insight-kicker" data-i18n="Result scope">Result scope</div>
      <div id="biInsightScope" class="bi-insight-note"></div>
    </div>
  </div>
</div>
```

with:

```html
<div id="biInsightPanel" class="bi-insight-panel bi-insight-strip mb-3" style="display:none;">
  <div class="bi-insight-grid">
    <div class="bi-insight-item bi-insight-question">
      <div class="bi-insight-kicker" data-i18n="Current question">Current question</div>
      <div id="biInsightQuestion" class="bi-insight-title"></div>
    </div>
    <div class="bi-insight-item">
      <div class="bi-insight-kicker" data-i18n="Top result">Top result</div>
      <div id="biInsightTop" class="bi-insight-value"></div>
    </div>
    <div class="bi-insight-item">
      <div class="bi-insight-kicker" data-i18n="Result scope">Result scope</div>
      <div id="biInsightScope" class="bi-insight-note"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Update the chart workspace markup**

Replace the opening chart card header section:

```html
<div id="biChartWrap" class="card mt-3" style="display:none;border:none;background:var(--bg-card);box-shadow:var(--shadow-md);">
  <div class="card-header d-flex align-items-center justify-content-between flex-wrap gap-2" style="background:var(--bg-card);border-bottom:2px solid var(--border-warm);">
    <span><i class="bi bi-bar-chart-fill me-2" style="color:var(--terracotta);"></i><span data-i18n="Chart">Chart</span></span>
    <div class="d-flex align-items-center gap-2 flex-wrap">
```

with:

```html
<div id="biChartWrap" class="card mt-3 bi-chart-workspace" style="display:none;">
  <div class="bi-chart-toolbar">
    <div class="bi-chart-title">
      <i class="bi bi-bar-chart-fill"></i>
      <span data-i18n="Chart">Chart</span>
    </div>
    <div class="bi-chart-controls">
```

Then replace the matching header closing `</div>` before `<div class="card-body"...>` with:

```html
    </div>
  </div>
```

Keep the chart metric selector and chart type toggle HTML unchanged inside the toolbar.

- [ ] **Step 3: Update the chart body class**

Replace:

```html
  <div class="card-body" style="height:320px;position:relative;">
```

with:

```html
  <div class="card-body bi-chart-canvas-shell">
```

- [ ] **Step 4: Update the results table wrapper**

Replace:

```html
<div id="biResults" class="mt-3" style="display:none;">
  <div class="card" style="border:none;background:var(--bg-card);box-shadow:var(--shadow-md);">
    <div class="card-header d-flex align-items-center justify-content-between" style="background:var(--bg-card);border-bottom:2px solid var(--border-warm);">
      <span><i class="bi bi-table me-2" style="color:var(--accent);"></i><span data-i18n="Query Results">Query Results</span>
        <span class="badge rounded-pill ms-2" id="resultCount" style="background:var(--accent);color:#fff;font-size:.7rem;"></span>
      </span>
    </div>
    <div class="table-responsive">
```

with:

```html
<div id="biResults" class="mt-3" style="display:none;">
  <div class="card bi-table-shell">
    <div class="bi-table-head">
      <span><i class="bi bi-table me-2"></i><span data-i18n="Query Results">Query Results</span>
        <span class="badge rounded-pill ms-2" id="resultCount"></span>
      </span>
    </div>
    <div class="table-responsive bi-table-scroll">
```

- [ ] **Step 5: Run the tests and verify markup hooks pass or fail only on missing CSS**

Run:

```powershell
python -m unittest tests.test_bi_ui_template.BiUiTemplateTests.test_bi_balanced_workspace_has_result_layers tests.test_bi_ui_template.BiUiTemplateTests.test_bi_mobile_and_table_polish_hooks_exist
```

Expected:

```text
FAIL: test_bi_mobile_and_table_polish_hooks_exist
AssertionError: '.bi-chart-workspace' not found
```

If both pass because the CSS was added in the same edit, continue to Task 4.

## Task 3: Refine BI-Scoped CSS in the Template

**Files:**
- Modify: `templates/bi/index.html`

- [ ] **Step 1: Replace the current insight panel CSS block**

Replace:

```css
  .bi-insight-panel {
    border: 1.5px solid var(--border-warm);
    background: linear-gradient(135deg, rgba(255,253,249,.98), rgba(246,243,238,.92));
    box-shadow: var(--shadow-sm);
  }
  .bi-insight-kicker {
    color: var(--text-secondary);
    font-size: .75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  .bi-insight-value {
    color: var(--accent);
    font-size: 1.25rem;
    font-weight: 800;
  }
  .bi-insight-note {
    color: var(--text-muted);
    font-size: .78rem;
  }
```

with:

```css
  .bi-insight-panel {
    width: 100%;
  }
  .bi-insight-strip {
    border: 1px solid rgba(90, 138, 106, .18);
    border-radius: 8px;
    background: rgba(255, 253, 249, .94);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
  }
  .bi-insight-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(180px, .95fr) minmax(150px, .7fr);
    gap: 0;
  }
  .bi-insight-item {
    min-width: 0;
    padding: .85rem 1rem;
    border-left: 1px solid rgba(90, 138, 106, .12);
  }
  .bi-insight-item:first-child {
    border-left: 0;
  }
  .bi-insight-question {
    background: rgba(90, 138, 106, .055);
  }
  .bi-insight-kicker {
    color: var(--text-secondary);
    font-size: .72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .04em;
  }
  .bi-insight-title {
    color: var(--text-primary);
    font-weight: 750;
    line-height: 1.35;
    margin-top: .2rem;
  }
  .bi-insight-value {
    color: var(--accent);
    font-size: 1.15rem;
    font-weight: 800;
    line-height: 1.25;
    margin-top: .2rem;
    overflow-wrap: anywhere;
  }
  .bi-insight-note {
    color: var(--text-muted);
    font-size: .82rem;
    font-weight: 650;
    margin-top: .25rem;
  }
```

- [ ] **Step 2: Add chart workspace CSS after the insight CSS**

Add:

```css
  .bi-chart-workspace {
    border: 1px solid rgba(90, 138, 106, .16) !important;
    border-radius: 8px;
    background: var(--bg-card) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: visible;
  }
  .bi-chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .85rem;
    padding: .8rem 1rem;
    border-bottom: 1px solid rgba(90, 138, 106, .14);
    background: rgba(255, 253, 249, .88);
  }
  .bi-chart-title {
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    color: var(--text-primary);
    font-weight: 800;
    min-width: max-content;
  }
  .bi-chart-title i {
    color: var(--terracotta);
  }
  .bi-chart-controls {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: .5rem;
    min-width: 0;
  }
  .bi-chart-canvas-shell {
    height: 340px;
    position: relative;
    padding: 1rem;
  }
```

- [ ] **Step 3: Add table shell CSS after the chart workspace CSS**

Add:

```css
  .bi-table-shell {
    border: 1px solid rgba(90, 138, 106, .13) !important;
    border-radius: 8px;
    background: var(--bg-card) !important;
    box-shadow: none !important;
    overflow: hidden;
  }
  .bi-table-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: .7rem 1rem;
    border-bottom: 1px solid rgba(90, 138, 106, .12);
    background: rgba(246, 243, 238, .55);
    color: var(--text-primary);
    font-weight: 800;
  }
  .bi-table-head i {
    color: var(--accent);
  }
  #resultCount {
    background: rgba(90, 138, 106, .12);
    color: var(--accent);
    font-size: .7rem;
    font-weight: 800;
  }
  .bi-table-scroll {
    overflow-x: auto;
    scrollbar-width: thin;
  }
  #biTable {
    min-width: 680px;
  }
  #biTable th {
    background: rgba(255, 253, 249, .96);
    color: var(--text-secondary);
    font-weight: 800;
  }
  #biTable td,
  #biTable th {
    vertical-align: middle;
    padding: .6rem .75rem;
  }
```

- [ ] **Step 4: Extend the existing mobile media query**

Inside the existing `@media (max-width: 767.98px)` block, after the `.bi-action-bar .btn` rule, add:

```css
    .bi-insight-grid {
      grid-template-columns: 1fr;
    }
    .bi-insight-item {
      border-left: 0;
      border-top: 1px solid rgba(90, 138, 106, .12);
    }
    .bi-insight-item:first-child {
      border-top: 0;
    }
    .bi-chart-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
    .bi-chart-controls,
    #chartMetricSelector {
      width: 100%;
      max-width: none !important;
    }
    .bi-chart-canvas-shell {
      height: 300px;
      padding: .75rem;
    }
    .bi-table-shell {
      position: relative;
    }
    .bi-table-shell::after {
      content: "";
      position: absolute;
      top: 3.05rem;
      right: 0;
      bottom: 0;
      width: 22px;
      pointer-events: none;
      background: linear-gradient(90deg, rgba(255,253,249,0), rgba(255,253,249,.95));
    }
```

- [ ] **Step 5: Run the focused tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_bi_ui_template.BiUiTemplateTests.test_bi_balanced_workspace_has_result_layers tests.test_bi_ui_template.BiUiTemplateTests.test_bi_mobile_and_table_polish_hooks_exist
```

Expected:

```text
..
OK
```

## Task 4: Keep Global BI CSS Consistent

**Files:**
- Modify: `static/css/style.css`

- [ ] **Step 1: Check whether global BI selectors conflict with the new scoped classes**

Run:

```powershell
rg -n "bi-chart-type-btn|bi-sortable|bi-preset-pill|bi-query-summary" static\css\style.css
```

Expected:

```text
static\css\style.css:1863:.bi-chart-type-btn {
static\css\style.css:1883:.bi-sortable {
static\css\style.css:1896:.bi-preset-pill {
static\css\style.css:1854:.bi-query-summary {
```

- [ ] **Step 2: If the chart type buttons still look too heavy, refine only the existing button selectors**

Replace the existing `.bi-chart-type-btn`, hover, and active blocks with:

```css
.bi-chart-type-btn {
  border: 1px solid rgba(90,138,106,.22) !important;
  background: rgba(255,253,249,.82);
  color: var(--text-muted);
  padding: .32rem .52rem;
  font-size: .85rem;
  transition: all .2s var(--ease);
}
.bi-chart-type-btn:hover {
  border-color: var(--accent) !important;
  color: var(--accent);
  background: rgba(90,138,106,.08);
}
.bi-chart-type-btn.active {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(61,107,78,.18);
}
```

- [ ] **Step 3: Leave `.bi-preset-pill` in place**

Do not remove `.bi-preset-pill` in `static/css/style.css`. It is unused by the current BI template but leaving it avoids unrelated CSS churn.

- [ ] **Step 4: Run the full BI template test file**

Run:

```powershell
python -m unittest tests.test_bi_ui_template
```

Expected:

```text
OK
```

## Task 5: Browser Verification

**Files:**
- No source edits unless verification exposes a concrete regression.

- [ ] **Step 1: Open the BI page**

Run the Flask app if it is not already running:

```powershell
python app.py
```

Then open:

```text
http://localhost:5000/bi
```

Expected:

```text
The BI page loads after login.
```

- [ ] **Step 2: Run a preset query**

In the browser:

```text
1. Log in as admin / admin123 if needed.
2. Select "Donation Value - Which donation channel brings the most value?"
3. Wait for the query to render.
```

Expected:

```text
The insight strip appears before the chart.
The chart appears before the Query Results table.
The chart metric selector and chart type buttons remain visible.
The result count badge appears in the table header.
```

- [ ] **Step 3: Check mobile layout**

Use browser dev tools or Playwright viewport:

```text
Width: 390px
Height: 844px
```

Expected:

```text
The control rail stacks above the output workspace.
The action bar remains reachable.
The insight strip stacks into one column.
The chart toolbar wraps without overlapping.
The table remains horizontally scrollable and does not squeeze columns into unreadable text.
```

- [ ] **Step 4: Check for console errors**

Run in Playwright or browser console:

```text
No new JavaScript errors should appear after selecting a preset and toggling chart type.
```

## Task 6: Final Review and Commit

**Files:**
- Commit only files changed for this implementation.

- [ ] **Step 1: Check status**

Run:

```powershell
git status --short
```

Expected:

```text
 M static/css/style.css
 M templates/bi/index.html
 M tests/test_bi_ui_template.py
```

Pre-existing unrelated files such as `elder_care.db`, `.playwright-mcp/`, screenshot files, or untracked test directories must not be included unless they were intentionally modified for this task.

- [ ] **Step 2: Review diff**

Run:

```powershell
git diff -- templates\bi\index.html static\css\style.css tests\test_bi_ui_template.py
```

Expected:

```text
The diff only contains BI workspace polish, regression tests, and scoped CSS refinements.
```

- [ ] **Step 3: Run final test command**

Run:

```powershell
python -m unittest tests.test_bi_ui_template
```

Expected:

```text
OK
```

- [ ] **Step 4: Commit implementation**

Run:

```powershell
git add -- templates\bi\index.html static\css\style.css tests\test_bi_ui_template.py
git commit -m "style(bi): polish balanced BI workspace"
```

Expected:

```text
[master <hash>] style(bi): polish balanced BI workspace
```

