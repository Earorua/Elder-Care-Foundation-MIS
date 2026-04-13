# BI Explorer Balanced Workspace Polish - Design Spec

**Date:** 2026-04-13
**Status:** Approved for planning
**Scope:** Visual and interaction polish for the BI Explorer page. Keep the current query model and backend API intact.

## Context

The BI Explorer already has a strong functional base:

- A question-led workflow through the Business Questions selector.
- Six data domains: Donors, Personnel, Events, Gifts, Finance, and Schedules.
- A left control rail with filters, dimensions, metrics, and actions.
- A right output workspace with insight summary, chart, and results table.
- Chart controls for chart type and charted metrics.
- URL hash query state and bilingual UI strings.

The next improvement should not rebuild the BI module. The selected direction is a balanced polish pass that improves professional feel and usability while preserving the existing layout, data definitions, query builder, and Chart.js implementation.

## Goals

1. Make the result area feel like a mature BI workspace instead of a generic form result page.
2. Keep the current "Business question + left control rail + right output workspace" structure.
3. Emphasize the decision flow: question, summary, chart, detail table.
4. Improve mobile usability without changing the product's behavior.
5. Stay within the current Elder Care visual system: warm backgrounds, green accents, terracotta action color, restrained borders, and compact operational copy.

## Non-Goals

- Add new BI metrics, dimensions, filters, or domains.
- Change SQL query construction or the `/api/bi/query` API contract.
- Change the database schema.
- Add saved queries, drill-down, cross-domain joins, or server-side pagination.
- Replace Chart.js or introduce a large new frontend dependency.
- Change the global application theme.

## Options Considered

### A. Low-Risk Polish

Small spacing, border, button, table-density, and mobile wrapping changes. This is lowest risk, but it would not add much visual hierarchy to the BI workflow.

### B. Balanced BI Workspace

Keep the current structure and strengthen the existing result flow:

- Better summary strip.
- Clearer chart workspace header and controls.
- Lighter left control rail.
- Detail table positioned as a supporting layer.
- Mobile flow tuned for reading and action stability.

This is the selected approach because it best matches the requested balance of presentation quality and practical usability.

### C. Presentation Cockpit

Large visual upgrade with a dashboard-like cockpit, prominent conclusion strip, and table drawer. This would be better for demos, but it changes the page rhythm more than needed and carries higher regression risk.

## Design

### 1. Page Structure

Keep the current two-column desktop workspace:

- Left: control rail, roughly 320-400px wide.
- Right: output workspace, fluid width.

The right output workspace should read in three layers:

1. Insight summary strip.
2. Chart workspace.
3. Query results table.

This preserves the current implementation shape while making the "answer first, details second" hierarchy clearer.

### 2. Control Rail

The control rail remains the main place for configuring a query:

- Business question selector stays at the top.
- Domain selector stays in the control rail.
- Filters, dimensions, and metrics remain grouped in builder cards.
- Run Query, Clear All, and Export CSV remain in the action area.

Polish changes:

- Reduce heavy nested-card feeling with lighter borders and calmer backgrounds.
- Keep selected tags compact and readable.
- Make the action area stable on mobile so query execution is easy to reach.
- Keep copy operational, not promotional.

### 3. Insight Summary Strip

Upgrade the existing insight panel into the first layer of the result workspace. It should visually communicate:

- Current question.
- Top result.
- Result scope.

The strip should use compact KPI-style blocks rather than a large alert-style panel. It should not overtake the chart, but it should provide immediate orientation after a query runs.

### 4. Chart Workspace

The chart area remains the primary visual object after a query:

- Keep chart before table.
- Keep the chart metric selector.
- Keep the chart type toggle.
- Keep the doughnut pagination behavior.

Polish changes:

- Make the chart header look like a workspace toolbar, not a generic card header.
- Improve spacing between title, metric selector, and chart type toggle.
- Keep chart canvas height stable across states.
- Use the existing palette and avoid introducing a new dashboard theme.
- Maintain responsive behavior so controls wrap cleanly on small screens.

### 5. Query Results Table

The results table remains visible and functional, but it should read as a detail layer:

- Keep result count.
- Keep sortable headers.
- Keep the existing table body rendering.
- Preserve CSV export behavior.

Polish changes:

- Make table chrome quieter than the chart.
- Add clearer horizontal overflow handling for mobile and narrow desktop.
- Keep header and cell spacing compact but readable.
- Avoid layout shifts when table data changes.

### 6. Mobile Layout

On mobile, the flow should be:

1. Page title and selected business question.
2. Query controls.
3. Sticky or clearly reachable action area.
4. Insight summary.
5. Chart.
6. Results table with horizontal scroll handling.

The goal is not to make BI tables fully card-based. The table can remain a table, but it must not compress text into unreadable columns.

## Implementation Scope

Expected files:

| File | Expected Changes |
| --- | --- |
| `templates/bi/index.html` | Adjust BI page structure classes, insight panel markup, chart header layout, results wrapper, and minimal JS state/class hooks if needed. |
| `static/css/style.css` | Add or refine BI-specific workspace, control rail, chart, table, and mobile styles. |
| `tests/test_bi_ui_template.py` | Update or extend template-level tests to protect the chart-before-table flow, business question workflow, and key structural classes. |

## Verification Plan

1. Run the BI template tests.
2. Open `/bi` on desktop and confirm the control rail, insight strip, chart workspace, and table render in the intended order.
3. Select at least one Business Question preset and confirm the query still runs.
4. Confirm chart controls still appear after a query.
5. Confirm table sorting and result count still exist.
6. Resize to mobile width and confirm the control flow, chart, and table remain usable.

## Approval Notes

The user approved:

- Direction C from the initial prompt: balance visual quality and usability.
- Option B from the visual comparison: Balanced BI Workspace.
- The page structure, visual details, mobile behavior, implementation scope, and verification plan described above.
