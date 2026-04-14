# AI Agent Recent History Sidebar Design

## Goal

Add a recent-question sidebar to the AI Agent page so users can reopen the last ten successful database questions after refreshing the page.

## Scope

The history belongs to the browser using the AI Agent page. It is persisted with `localStorage`, not written to SQLite. Each record stores the question, generated SQL, natural-language answer, returned columns, returned preview rows, total row count, and the time the record was saved.

The feature is limited to the AI Agent page. It does not change the AI query endpoint, database schema, or access-control model.

## User Experience

The existing right-side Agent context column gains a "Recent Questions" panel. The newest record appears first, and the list is capped at ten items. Each list item shows a compact question preview and saved time. If no history exists, the panel shows an empty state.

Clicking a saved question restores the saved answer into the main answer area, updates the latest SQL trace, and renders the saved result rows in the existing result table. The question textbox also receives the saved question so users can rerun or edit it.

After a successful new AI Agent request, the page saves the record automatically, moves it to the top of the list, removes older duplicate entries for the same question and SQL, and trims the list to ten records.

## Architecture

Implement the feature in `templates/agent/index.html` because the API already returns all data needed for history rendering. Use a small set of JavaScript helpers for loading, saving, rendering, selecting, and formatting history entries. Use a dedicated `localStorage` key so the feature is isolated from other page state.

No backend code is needed.

## Error Handling

If `localStorage` is unavailable or contains malformed JSON, the page falls back to an empty in-memory list for the current load. A failed AI request is not saved to history because it does not include a complete SQL/result payload.

## Testing

Add template-level tests in `tests/test_agent_helpers.py` to confirm the page contains the history panel hooks, `localStorage` persistence helpers, ten-item cap, and i18n keys for new user-facing copy.
