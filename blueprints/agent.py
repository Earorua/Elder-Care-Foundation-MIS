import json
import re
from http.client import RemoteDisconnected
from urllib import error as urlerror
from urllib import request as urlrequest

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from db import get_db
from blueprints.auth import role_required
from blueprints.bi import (
    DIMENSION_DEFS,
    DOMAIN_BASES,
    FILTER_DEFS,
    METRIC_DEFS,
    VALID_DOMAINS,
)


agent_bp = Blueprint("agent", __name__)

DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4.6"
OPENROUTER_MODEL_OPTIONS = [
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.7",
    "openai/gpt-5.4",
    "google/gemini-3.1-pro-preview",
    "z-ai/glm-5.1",
]

BLOCKED_SQL_WORDS = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "update",
    "vacuum",
}

ENUM_CONTEXT_COLUMN_KEYWORDS = (
    "category",
    "gender",
    "location",
    "method",
    "role",
    "source",
    "status",
    "type",
)

MAX_ENUM_CONTEXT_VALUES = 20

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

SQL_ALIAS_RESERVED_WORDS = {
    "cross",
    "full",
    "group",
    "inner",
    "join",
    "left",
    "limit",
    "on",
    "order",
    "outer",
    "right",
    "where",
}


@agent_bp.route("/agent")
@login_required
@role_required("finance", "event_coordinator")
def agent_index():
    model_options = _agent_model_options()
    return render_template(
        "agent/index.html",
        model_name=_default_agent_model(model_options),
        model_options=model_options,
        row_limit=current_app.config.get("AGENT_ROW_LIMIT", 200),
    )


@agent_bp.route("/api/agent/query", methods=["POST"])
@login_required
def agent_query():
    if not current_app.config.get("LOGIN_DISABLED") and not current_user.has_role("finance", "event_coordinator"):
        return jsonify(error="Insufficient permissions to use the AI Agent."), 403

    api_key = current_app.config.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return jsonify(error="Set OPENROUTER_API_KEY in config.py before using the AI Agent."), 400

    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()
    if not question:
        return jsonify(error="Enter a database question first."), 400
    try:
        selected_model = _select_agent_model(body)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    stage = "generating SQL"
    try:
        schema = _get_database_schema()
        sql_payload = _generate_sql_payload(question, schema, model=selected_model)
        sql_payload = _repair_sql_semantics_if_needed(question, schema, sql_payload, model=selected_model)
        stage = "executing SQL"
        sql = _ensure_limit(
            _validate_readonly_sql(sql_payload.get("sql", "")),
            current_app.config.get("AGENT_ROW_LIMIT", 200),
        )
        cur = get_db().execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        cur.close()
        result_rows = _rows_to_dicts(rows)
        stage = "generating answer"
        answer = _call_openrouter(
            _build_answer_prompt(question, sql, columns, result_rows),
            max_tokens=900,
            temperature=0.2,
            model=selected_model,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except urlerror.HTTPError as exc:
        return jsonify(error=_http_error_message(stage, exc)), _http_status_code(exc)
    except urlerror.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            return jsonify(error=_timeout_message(stage)), 504
        return jsonify(error=f"OpenRouter request failed: {exc.reason}"), 502
    except TimeoutError:
        return jsonify(error=_timeout_message(stage)), 504
    except RemoteDisconnected:
        return jsonify(error=_connection_message(stage)), 502
    except Exception as exc:
        return jsonify(error=f"AI Agent failed: {exc}"), 500

    return jsonify(
        answer=answer,
        sql=sql,
        rationale=sql_payload.get("rationale", ""),
        columns=columns,
        rows=result_rows[:50],
        total_rows=len(result_rows),
        model=selected_model,
    )


def _agent_model_options():
    options = current_app.config.get("OPENROUTER_MODEL_OPTIONS", OPENROUTER_MODEL_OPTIONS)
    cleaned = []
    for option in options:
        value = str(option).strip()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned or list(OPENROUTER_MODEL_OPTIONS)


def _default_agent_model(model_options=None):
    options = model_options or _agent_model_options()
    configured_model = str(current_app.config.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)).strip()
    return configured_model if configured_model in options else options[0]


def _select_agent_model(body):
    requested_model = str(body.get("model") or "").strip()
    model_options = _agent_model_options()
    if not requested_model:
        return _default_agent_model(model_options)
    if requested_model not in model_options:
        raise ValueError("Select a supported OpenRouter model.")
    return requested_model


def _strip_sql_fences(sql):
    text = (sql or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _validate_readonly_sql(sql):
    cleaned = _strip_sql_fences(sql).rstrip(";").strip()
    if not cleaned:
        raise ValueError("The model did not return SQL.")
    if ";" in cleaned:
        raise ValueError("Only one read-only SQL statement is allowed.")

    first_word = re.match(r"^\s*([A-Za-z]+)", cleaned)
    if not first_word or first_word.group(1).lower() not in {"select", "with"}:
        raise ValueError("Only SELECT or WITH queries are allowed.")

    tokens = set(re.findall(r"\b[a-z_]+\b", cleaned.lower()))
    blocked = sorted(tokens & BLOCKED_SQL_WORDS)
    if blocked:
        raise ValueError(f"Read-only SQL rejected because it contains: {', '.join(blocked)}.")

    return cleaned


def _ensure_limit(sql, limit):
    if _has_top_level_limit(sql):
        return sql
    return f"{sql} LIMIT {int(limit)}"


def _has_top_level_limit(sql):
    depth = 0
    quote = None
    lower_sql = sql.lower()
    i = 0
    while i < len(sql):
        char = sql[i]
        if quote:
            if char == quote:
                next_char = sql[i + 1] if i + 1 < len(sql) else ""
                if next_char == quote:
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif depth == 0 and lower_sql.startswith("limit", i):
            before = lower_sql[i - 1] if i else " "
            after = lower_sql[i + 5] if i + 5 < len(lower_sql) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return re.match(r"limit\s+\d+\b", lower_sql[i:]) is not None
        i += 1
    return False


def _get_database_schema():
    db = get_db()
    table_rows = db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    parts = []
    for table_row in table_rows:
        table_name = table_row["name"]
        safe_table_name = table_name.replace('"', '""')
        columns = db.execute(f'PRAGMA table_info("{safe_table_name}")').fetchall()
        column_text = ", ".join(f"{col['name']} {col['type'] or 'TEXT'}" for col in columns)
        parts.append(f"{table_name}: {column_text}")
    parts.append("")
    parts.append(_get_business_semantic_context())
    parts.append("")
    parts.append(_get_business_concept_alias_context())
    parts.append("")
    parts.append(_get_bi_metadata_context())
    parts.append("")
    parts.append(_format_enum_value_context(_get_enum_values_by_column(db)))
    return "\n".join(parts)


def _get_business_semantic_context():
    return "\n".join(
        [
            "Business semantic notes:",
            "- In broad people questions, staff members, staff, and personnel refer to records in persons.",
            "- Do not filter persons.person_type to Staff unless the database enum values include Staff.",
            "- persons.person_type currently distinguishes employment/participation categories such as Employee and Volunteer.",
            "- People/personnel/staff who are also donors are matched by email: LOWER(persons.email) = LOWER(donors.email).",
            "- Donations belong to donors through donations.donor_id = donors.donor_id.",
            "- Events and donors are linked through donors_events.",
            "- Schedules belong to persons and events through schedules.person_id and schedules.event_id.",
            "- Gifts are distributed through gift_batch and gift_distribution; gift_distribution.donation_id links back to donations.",
        ]
    )


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


def _get_enum_values_by_column(db=None):
    db = db or get_db()
    enum_values = {}
    table_rows = db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    for table_row in table_rows:
        table_name = table_row["name"]
        safe_table_name = table_name.replace('"', '""')
        columns = db.execute(f'PRAGMA table_info("{safe_table_name}")').fetchall()
        for col in columns:
            column_name = col["name"]
            if not _is_enum_context_column(column_name, col["type"] or ""):
                continue
            safe_column_name = column_name.replace('"', '""')
            rows = db.execute(
                f'SELECT DISTINCT "{safe_column_name}" AS value '
                f'FROM "{safe_table_name}" '
                f'WHERE "{safe_column_name}" IS NOT NULL '
                f'AND TRIM(CAST("{safe_column_name}" AS TEXT)) != "" '
                f'ORDER BY "{safe_column_name}" '
                f"LIMIT {MAX_ENUM_CONTEXT_VALUES + 1}"
            ).fetchall()
            values = [str(row["value"]) for row in rows]
            if values and len(values) <= MAX_ENUM_CONTEXT_VALUES:
                enum_values[f"{table_name}.{column_name}"] = values
    return enum_values


def _is_enum_context_column(column_name, column_type):
    name = column_name.lower()
    sql_type = column_type.upper()
    return (
        any(keyword in name for keyword in ENUM_CONTEXT_COLUMN_KEYWORDS)
        and ("TEXT" in sql_type or "CHAR" in sql_type or not sql_type)
    )


def _format_enum_value_context(enum_values):
    lines = ["Observed enum-like values:"]
    if not enum_values:
        lines.append("- None detected.")
        return "\n".join(lines)
    for column_key, values in enum_values.items():
        lines.append(f"- {column_key} values: {', '.join(values)}")
    return "\n".join(lines)


def _repair_sql_semantics_if_needed(question, schema, sql_payload, model=None):
    issues = _find_unknown_enum_filters(
        sql_payload.get("sql", ""),
        _get_enum_values_by_column(),
    )
    if not issues:
        return sql_payload

    repair_response = _call_openrouter(
        _build_sql_semantic_repair_prompt(question, schema, sql_payload, issues),
        max_tokens=700,
        temperature=0,
        model=model,
    )
    return _extract_json_object(repair_response)


def _find_unknown_enum_filters(sql, enum_values_by_column):
    alias_map = _extract_table_aliases(sql)
    issues = []
    seen = set()
    for column_key, valid_values in enum_values_by_column.items():
        table_name, column_name = column_key.split(".", 1)
        qualifiers = {
            alias
            for alias, table in alias_map.items()
            if table.lower() == table_name.lower()
        }
        if not qualifiers:
            qualifiers = {table_name.lower()}

        for qualifier in qualifiers:
            used_values = _extract_enum_filter_values(sql, qualifier, column_name)
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
    return issues


def _extract_table_aliases(sql):
    aliases = {}
    for match in re.finditer(
        r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s+(?:as\s+)?([A-Za-z_][A-Za-z0-9_]*))?",
        sql or "",
        flags=re.IGNORECASE,
    ):
        table_name = match.group(1)
        alias = match.group(2)
        aliases[table_name.lower()] = table_name
        if alias and alias.lower() not in SQL_ALIAS_RESERVED_WORDS:
            aliases[alias.lower()] = table_name
    return aliases


def _extract_enum_filter_values(sql, qualifier, column_name):
    if not sql:
        return []
    qualified_column = rf"{re.escape(qualifier)}\s*\.\s*{re.escape(column_name)}"
    column_expr = rf"(?:LOWER\(\s*)?{qualified_column}(?:\s*\))?"
    values = []
    for match in re.finditer(
        rf"{column_expr}\s*=\s*'([^']*)'",
        sql,
        flags=re.IGNORECASE,
    ):
        values.append(match.group(1))
    for match in re.finditer(
        rf"{column_expr}\s+IN\s*\(([^)]*)\)",
        sql,
        flags=re.IGNORECASE,
    ):
        values.extend(re.findall(r"'([^']*)'", match.group(1)))
    return values


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


def _is_known_enum_value(value, valid_values):
    normalized = value.strip().lower()
    return normalized in {valid_value.strip().lower() for valid_value in valid_values}


def _extract_json_object(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("The model did not return a JSON object containing SQL.")
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"The model returned malformed JSON: {exc.msg}.") from exc


def _generate_sql_payload(question, schema, model=None):
    raw_response = _call_openrouter(
        _build_sql_prompt(question, schema),
        max_tokens=700,
        temperature=0.1,
        model=model,
    )
    try:
        return _extract_json_object(raw_response)
    except ValueError as first_error:
        _log_non_json_sql_response(raw_response, first_error)

    repair_response = _call_openrouter(
        _build_sql_repair_prompt(question, schema, raw_response),
        max_tokens=700,
        temperature=0,
        model=model,
    )
    try:
        return _extract_json_object(repair_response)
    except ValueError as second_error:
        raise ValueError(f"{second_error} The automatic JSON repair attempt also failed.") from second_error


def _log_non_json_sql_response(raw_response, error):
    if current_app.debug or current_app.config.get("AGENT_LOG_MODEL_OUTPUT"):
        current_app.logger.warning(
            "OpenRouter SQL generation returned non-JSON (%s). Raw response: %r",
            error,
            (raw_response or "")[:1000],
        )


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


def _timeout_message(stage):
    timeout = current_app.config.get("OPENROUTER_TIMEOUT", 120)
    return (
        f"OpenRouter request timed out while {stage} after {timeout} seconds. "
        "Try again with a narrower question, or increase OPENROUTER_TIMEOUT in config.py."
    )


def _connection_message(stage):
    return (
        f"OpenRouter closed the connection while {stage}. "
        "This usually means the remote API, network, proxy, or model endpoint dropped the request. "
        "Try again, or verify OPENROUTER_BASE_URL, OPENROUTER_MODEL, and network access."
    )


def _http_error_message(stage, exc):
    status = getattr(exc, "code", None)
    reason = getattr(exc, "reason", None) or getattr(exc, "msg", None) or "HTTP error"
    if status in (429, 500, 502, 503, 504):
        return (
            f"OpenRouter returned HTTP {status} ({reason}) while {stage}. "
            "This is usually a temporary upstream or model availability issue. "
            "Try again, ask a narrower question, or verify OPENROUTER_BASE_URL and OPENROUTER_MODEL in config.py."
        )
    if status in (401, 403):
        return (
            f"OpenRouter returned HTTP {status} ({reason}) while {stage}. "
            "Verify OPENROUTER_API_KEY in config.py or your environment."
        )
    return (
        f"OpenRouter returned HTTP {status} ({reason}) while {stage}. "
        "Verify OPENROUTER_API_KEY, OPENROUTER_BASE_URL, and OPENROUTER_MODEL in config.py."
    )


def _http_status_code(exc):
    status = getattr(exc, "code", 502)
    if status in (429, 503, 504):
        return status
    if status in (401, 403):
        return 502
    return 502


def _build_sql_prompt(question, schema):
    return (
        "You are a database analyst for an elder care foundation MIS.\n"
        "Return exactly one JSON object with keys sql and rationale. "
        "The sql must be a single read-only SQLite SELECT or WITH query. "
        "Do not use PRAGMA or any mutation statement. "
        "Use the business semantic notes, observed enum-like values, and join paths in the schema context. "
        "Do not invent enum values that are not listed in the schema context. "
        "If a user term is a business synonym, map it to the documented table or valid enum values instead of filtering on the literal term.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}"
    )


def _build_sql_repair_prompt(question, schema, raw_response):
    return (
        "The previous model output did not follow the required SQL JSON format.\n"
        "Return exactly one JSON object with keys sql and rationale. "
        "Do not include markdown, prose, or any text outside the JSON object. "
        "The sql must be a single read-only SQLite SELECT or WITH query. "
        "Do not use PRAGMA or any mutation statement. "
        "Use the business semantic notes, observed enum-like values, and join paths in the schema context. "
        "Do not invent enum values that are not listed in the schema context.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}\n\n"
        f"Previous model output:\n{raw_response}"
    )


def _build_sql_semantic_repair_prompt(question, schema, sql_payload, issues):
    return (
        "The previous SQL used unsupported enum values or treated business entity synonyms as enum values for this database.\n"
        "Return exactly one JSON object with keys sql and rationale. "
        "Do not include markdown, prose, or any text outside the JSON object. "
        "The sql must be a single read-only SQLite SELECT or WITH query. "
        "Do not use PRAGMA or any mutation statement. "
        "Use the business semantic notes, observed enum-like values, and join paths in the schema context. "
        "If the user used a documented business synonym, map it to the documented table or valid enum values. "
        "If the user explicitly asked for a value that is not present and is not a synonym, keep the user's intent and return a query that reports no matching rows instead of dropping the filter.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}\n\n"
        f"Unsupported enum values:\n{json.dumps(issues, ensure_ascii=False)}\n\n"
        f"Previous SQL payload:\n{json.dumps(sql_payload, ensure_ascii=False)}"
    )


def _build_answer_prompt(question, sql, columns, rows):
    return (
        "You are answering a staff user's database question. "
        "Answer directly in natural language using only the SQL result rows below. "
        "Use the same language as the user's question. "
        "Do not return a table, JSON, CSV, or raw detail rows. "
        "If the result is empty, say that no matching rows were found.\n\n"
        f"Question: {question}\n"
        f"SQL: {sql}\n"
        f"Columns: {json.dumps(columns, ensure_ascii=False)}\n"
        f"Rows: {json.dumps(rows, ensure_ascii=False, default=str)}"
    )


def _call_openrouter(prompt, max_tokens=800, temperature=0.2, model=None):
    api_key = current_app.config.get("OPENROUTER_API_KEY", "")
    base_url = current_app.config.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    selected_model = model or current_app.config.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    payload = {
        "model": selected_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urlrequest.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = current_app.config.get("OPENROUTER_TIMEOUT", 120)
    max_retries = max(0, int(current_app.config.get("OPENROUTER_MAX_RETRIES", 2)))
    for attempt in range(max_retries + 1):
        try:
            with _open_openrouter_request(req, timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except (RemoteDisconnected, urlerror.URLError) as exc:
            if attempt >= max_retries or not _is_retryable_openrouter_error(exc):
                raise
    return data["choices"][0]["message"]["content"].strip()


def _is_retryable_openrouter_error(exc):
    if isinstance(exc, RemoteDisconnected):
        return True
    if isinstance(exc, urlerror.HTTPError):
        return getattr(exc, "code", None) in (429, 500, 502, 503, 504)
    if isinstance(exc, urlerror.URLError):
        return isinstance(getattr(exc, "reason", None), RemoteDisconnected)
    return False


def _open_openrouter_request(req, timeout):
    if current_app.config.get("OPENROUTER_DISABLE_ENV_PROXY", True):
        opener = urlrequest.build_opener(urlrequest.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urlrequest.urlopen(req, timeout=timeout)


_call_siliconflow = _call_openrouter
_open_siliconflow_request = _open_openrouter_request
