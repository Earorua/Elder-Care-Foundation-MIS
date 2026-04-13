# AI Agent Page Design

## Goal

Add a standalone AI Agent page that answers natural-language questions about the full SQLite database by calling SiliconFlow's `Qwen/Qwen3.5-4B` model and running read-only dynamic SQL against `elder_care.db`.

## Scope

The feature adds an authenticated `/agent` page under the Analytics navigation group. Users can ask questions about any table and any row in the bundled database. The Agent may inspect schema and execute dynamically generated detail queries, but it must not mutate data.

The page will not replace BI Explorer. BI Explorer remains the structured chart/query builder; AI Agent is the free-form question-answering surface.

## Architecture

Create a new Flask blueprint `blueprints/agent.py` with:

- `GET /agent` to render the page.
- `POST /api/agent/query` to accept a natural-language question, call SiliconFlow, execute validated read-only SQL, and return the final answer plus query trace.

Register the blueprint in `app.py`. Add `templates/agent/index.html` for the UI and add the sidebar link in `templates/base.html` under Analytics for finance and event coordinator roles, matching BI Explorer's access pattern.

Add SiliconFlow configuration in `config.py`:

- `SILICONFLOW_API_KEY = ''`
- `SILICONFLOW_BASE_URL = 'https://api.siliconflow.cn/v1'`
- `SILICONFLOW_MODEL = 'Qwen/Qwen3.5-4B'`

The user will paste the API key into `config.py` between the quotes for `SILICONFLOW_API_KEY`.

## Data Flow

1. Browser sends the user's question to `/api/agent/query`.
2. Backend reads the SQLite schema with `sqlite_master` and `PRAGMA table_info`.
3. Backend asks SiliconFlow to produce a JSON object containing a read-only SQL query and a short rationale.
4. Backend validates the SQL before execution:
   - Allow only a single statement.
   - Allow only `SELECT` or `WITH` queries.
   - Reject mutation keywords such as `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `ATTACH`, `DETACH`, `VACUUM`, and `PRAGMA`.
   - Enforce a row limit if the generated query does not already include one.
5. Backend executes the SQL against the existing Flask SQLite connection.
6. Backend sends the question, SQL, columns, and capped result rows back to SiliconFlow to generate a concise business answer.
7. Browser renders the answer, SQL trace, row count, and a small result preview.

## UI Design

Use a standalone app workspace, not a landing page. The first screen contains the working Agent interface:

- Header: "AI Agent" with short operational copy: "Ask questions across the full database."
- Main chat column: question input, send button, answer area, and starter prompts.
- Side context column: model name, database access scope, read-only status, and latest SQL trace.
- Result preview: compact table for returned rows when available.

The layout follows the existing Botanical Warmth style while keeping the workspace restrained and utility-focused. It uses existing Bootstrap, Bootstrap Icons, and global CSS variables. No new external frontend dependency is required.

## Error Handling

If `SILICONFLOW_API_KEY` is empty, the API returns a clear setup error telling the user to paste the key into `config.py`.

If SiliconFlow returns malformed JSON for SQL generation, the API returns an actionable error instead of executing anything.

If SQL validation fails, the API rejects the query and reports that only read-only database questions are allowed.

If the model call or database query fails, the API returns a short error message suitable for display in the Agent page.

## Testing

Add focused unit tests for the backend helper functions:

- Schema extraction includes table and column metadata.
- SQL validation accepts simple read-only `SELECT` queries.
- SQL validation rejects mutation statements and multiple statements.
- Row-limit enforcement adds a default limit to unlimited selects and preserves existing limits.

Where practical, test the Flask endpoint's missing-key path so the user receives a clear setup instruction before providing a real API key. External SiliconFlow calls are not made in automated tests.

## Security Notes

The user requested full database visibility for this Agent. The implementation will honor that by exposing all tables and detail rows to authenticated Analytics users, while still enforcing read-only SQL execution to prevent accidental database mutation.
