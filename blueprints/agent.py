import json
import re
from http.client import RemoteDisconnected
from urllib import error as urlerror
from urllib import request as urlrequest

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from db import get_db
from blueprints.auth import role_required


agent_bp = Blueprint("agent", __name__)

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


@agent_bp.route("/agent")
@login_required
@role_required("finance", "event_coordinator")
def agent_index():
    return render_template(
        "agent/index.html",
        model_name=current_app.config.get("SILICONFLOW_MODEL", "Pro/zai-org/GLM-5.1"),
        row_limit=current_app.config.get("AGENT_ROW_LIMIT", 200),
    )


@agent_bp.route("/api/agent/query", methods=["POST"])
@login_required
def agent_query():
    if not current_app.config.get("LOGIN_DISABLED") and not current_user.has_role("finance", "event_coordinator"):
        return jsonify(error="Insufficient permissions to use the AI Agent."), 403

    api_key = current_app.config.get("SILICONFLOW_API_KEY", "")
    if not api_key:
        return jsonify(error="Set SILICONFLOW_API_KEY in config.py before using the AI Agent."), 400

    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()
    if not question:
        return jsonify(error="Enter a database question first."), 400

    stage = "generating SQL"
    try:
        schema = _get_database_schema()
        sql_payload = _generate_sql_payload(question, schema)
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
        answer = _call_siliconflow(
            _build_answer_prompt(question, sql, columns, result_rows),
            max_tokens=900,
            temperature=0.2,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except urlerror.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            return jsonify(error=_timeout_message(stage)), 504
        return jsonify(error=f"SiliconFlow request failed: {exc.reason}"), 502
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
    )


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
    return "\n".join(parts)


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


def _generate_sql_payload(question, schema):
    raw_response = _call_siliconflow(
        _build_sql_prompt(question, schema),
        max_tokens=700,
        temperature=0.1,
    )
    try:
        return _extract_json_object(raw_response)
    except ValueError as first_error:
        _log_non_json_sql_response(raw_response, first_error)

    repair_response = _call_siliconflow(
        _build_sql_repair_prompt(question, schema, raw_response),
        max_tokens=700,
        temperature=0,
    )
    try:
        return _extract_json_object(repair_response)
    except ValueError as second_error:
        raise ValueError(f"{second_error} The automatic JSON repair attempt also failed.") from second_error


def _log_non_json_sql_response(raw_response, error):
    if current_app.debug or current_app.config.get("AGENT_LOG_MODEL_OUTPUT"):
        current_app.logger.warning(
            "SiliconFlow SQL generation returned non-JSON (%s). Raw response: %r",
            error,
            (raw_response or "")[:1000],
        )


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


def _timeout_message(stage):
    timeout = current_app.config.get("SILICONFLOW_TIMEOUT", 120)
    return (
        f"SiliconFlow request timed out while {stage} after {timeout} seconds. "
        "Try again with a narrower question, or increase SILICONFLOW_TIMEOUT in config.py."
    )


def _connection_message(stage):
    return (
        f"SiliconFlow closed the connection while {stage}. "
        "This usually means the remote API, network, proxy, or model endpoint dropped the request. "
        "Try again, or verify SILICONFLOW_BASE_URL, SILICONFLOW_MODEL, and network access."
    )


def _build_sql_prompt(question, schema):
    return (
        "You are a database analyst for an elder care foundation MIS.\n"
        "Return exactly one JSON object with keys sql and rationale. "
        "The sql must be a single read-only SQLite SELECT or WITH query. "
        "Do not use PRAGMA or any mutation statement.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}"
    )


def _build_sql_repair_prompt(question, schema, raw_response):
    return (
        "The previous model output did not follow the required SQL JSON format.\n"
        "Return exactly one JSON object with keys sql and rationale. "
        "Do not include markdown, prose, or any text outside the JSON object. "
        "The sql must be a single read-only SQLite SELECT or WITH query. "
        "Do not use PRAGMA or any mutation statement.\n\n"
        f"Database schema:\n{schema}\n\n"
        f"Question: {question}\n\n"
        f"Previous model output:\n{raw_response}"
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


def _call_siliconflow(prompt, max_tokens=800, temperature=0.2):
    api_key = current_app.config.get("SILICONFLOW_API_KEY", "")
    base_url = current_app.config.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
    model = current_app.config.get("SILICONFLOW_MODEL", "Pro/zai-org/GLM-5.1")
    payload = {
        "model": model,
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
    timeout = current_app.config.get("SILICONFLOW_TIMEOUT", 120)
    with urlrequest.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()
