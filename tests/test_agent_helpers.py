import json
import os
import sqlite3
import tempfile
import unittest
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import MagicMock, patch

import blueprints.agent as agent_module
from flask import Flask

from blueprints.agent import (
    _build_answer_prompt,
    _ensure_limit,
    _extract_json_object,
    _get_database_schema,
    _rows_to_dicts,
    _validate_readonly_sql,
    agent_bp,
)
from db import init_app


ROOT = Path(__file__).resolve().parents[1]


class AgentHelperTests(unittest.TestCase):
    def test_default_openrouter_provider_configuration_is_requested_model(self):
        expected_model = "anthropic/claude-sonnet-4.6"
        expected_base_url = "https://openrouter.ai/api/v1"
        expected_models = [
            "anthropic/claude-sonnet-4.6",
            "anthropic/claude-opus-4.7",
            "openai/gpt-5.4",
            "google/gemini-3.1-pro-preview",
            "z-ai/glm-5.1",
        ]
        config_py = (ROOT / "config.py").read_text(encoding="utf-8")
        agent_py = (ROOT / "blueprints" / "agent.py").read_text(encoding="utf-8")

        self.assertIn("OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY',", config_py)
        self.assertIn(f"OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', '{expected_base_url}')", config_py)
        self.assertIn(f"OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', '{expected_model}')", config_py)
        self.assertIn("OPENROUTER_MODEL_OPTIONS", config_py)
        self.assertIn("OPENROUTER_API_KEY", agent_py)
        self.assertIn(expected_base_url, agent_py)
        self.assertIn(expected_model, agent_py)
        for model in expected_models:
            with self.subTest(model=model):
                self.assertIn(model, config_py)
                self.assertIn(model, agent_py)

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

    def test_ensure_limit_ignores_nested_limit_when_outer_query_is_unlimited(self):
        self.assertEqual(
            _ensure_limit("WITH x AS (SELECT * FROM donors LIMIT 5) SELECT * FROM x", 200),
            "WITH x AS (SELECT * FROM donors LIMIT 5) SELECT * FROM x LIMIT 200",
        )

    def test_get_database_schema_includes_table_and_column_metadata(self):
        app, db_path = self._make_temp_app()
        try:
            with app.app_context():
                schema = _get_database_schema()
        finally:
            os.unlink(db_path)

        self.assertIn("donors", schema)
        self.assertIn("donor_id INTEGER", schema)
        self.assertIn("name TEXT", schema)

    def test_get_database_schema_includes_semantic_notes_and_enum_values(self):
        app, db_path = self._make_temp_app()
        try:
            with app.app_context():
                schema = _get_database_schema()
        finally:
            os.unlink(db_path)

        self.assertIn("Business semantic notes", schema)
        self.assertIn("staff members", schema)
        self.assertIn("persons.person_type values: Employee, Volunteer", schema)
        self.assertIn("LOWER(persons.email) = LOWER(donors.email)", schema)

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

    def test_agent_query_returns_setup_error_when_api_key_missing(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = ""
        try:
            response = app.test_client().post("/api/agent/query", json={"question": "How many donors?"})
        finally:
            os.unlink(db_path)

        self.assertEqual(response.status_code, 400)
        self.assertIn("OPENROUTER_API_KEY", response.get_json()["error"])

    def test_extract_json_object_accepts_fenced_model_output(self):
        parsed = _extract_json_object(
            '```json\n{"sql": "SELECT * FROM donors", "rationale": "List donors"}\n```'
        )

        self.assertEqual(parsed["sql"], "SELECT * FROM donors")
        self.assertEqual(parsed["rationale"], "List donors")

    def test_rows_to_dicts_returns_json_safe_values(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE sample (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO sample VALUES (1, 'Ada')")
        rows = conn.execute("SELECT * FROM sample").fetchall()

        self.assertEqual(_rows_to_dicts(rows), [{"id": 1, "name": "Ada"}])

    def test_call_openrouter_disables_environment_proxy_by_default(self):
        app, db_path = self._make_temp_app()
        app.config["OPENROUTER_API_KEY"] = "test-key"
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": " ok "}}]}
        ).encode("utf-8")
        opener = MagicMock()
        opener.open.return_value = response
        proxy_handler = object()

        try:
            with app.app_context():
                with patch(
                    "blueprints.agent.urlrequest.ProxyHandler",
                    return_value=proxy_handler,
                ) as mock_proxy_handler:
                    with patch(
                        "blueprints.agent.urlrequest.build_opener",
                        return_value=opener,
                    ) as mock_build_opener:
                        with patch(
                            "blueprints.agent.urlrequest.urlopen",
                            side_effect=AssertionError("urlopen should not be used"),
                        ):
                            result = agent_module._call_openrouter("hello")
        finally:
            os.unlink(db_path)

        self.assertEqual(result, "ok")
        mock_proxy_handler.assert_called_once_with({})
        mock_build_opener.assert_called_once_with(proxy_handler)
        opener.open.assert_called_once()
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 120)

    def test_call_openrouter_retries_remote_disconnect(self):
        app, db_path = self._make_temp_app()
        app.config["OPENROUTER_API_KEY"] = "test-key"
        app.config["OPENROUTER_MAX_RETRIES"] = 1
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": " recovered "}}]}
        ).encode("utf-8")

        try:
            with app.app_context():
                with patch(
                    "blueprints.agent._open_openrouter_request",
                    side_effect=[
                        RemoteDisconnected("Remote end closed connection without response"),
                        response,
                    ],
                ) as mock_open:
                    result = agent_module._call_openrouter("hello")
        finally:
            os.unlink(db_path)

        self.assertEqual(result, "recovered")
        self.assertEqual(mock_open.call_count, 2)

    def test_call_openrouter_uses_selected_model_override(self):
        app, db_path = self._make_temp_app()
        app.config["OPENROUTER_API_KEY"] = "test-key"
        app.config["OPENROUTER_MODEL"] = "anthropic/claude-sonnet-4.6"
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": " ok "}}]}
        ).encode("utf-8")

        try:
            with app.app_context():
                with patch("blueprints.agent._open_openrouter_request", return_value=response) as mock_open:
                    result = agent_module._call_openrouter("hello", model="openai/gpt-5.4")
        finally:
            os.unlink(db_path)

        self.assertEqual(result, "ok")
        request = mock_open.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "openai/gpt-5.4")

    def test_answer_prompt_requires_direct_answer_in_user_language(self):
        prompt = _build_answer_prompt(
            "哪些捐款人捐了 100 美元？",
            "SELECT name, amount FROM donors LIMIT 200",
            ["name", "amount"],
            [{"name": "Ada", "amount": 100.0}],
        )

        self.assertIn("Answer directly in natural language", prompt)
        self.assertIn("Use the same language as the user's question", prompt)
        self.assertIn("Do not return a table, JSON, CSV, or raw detail rows", prompt)

    def test_agent_query_returns_answer_and_table_data(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=[
                    '{"sql": "SELECT name, amount FROM donors", "rationale": "Find matching donors."}',
                    "Ada donated $100.00.",
                ],
            ):
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "Who donated $100?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["answer"], "Ada donated $100.00.")
        self.assertEqual(payload["total_rows"], 1)
        self.assertEqual(payload["columns"], ["name", "amount"])
        self.assertEqual(payload["rows"], [{"name": "Ada", "amount": 100.0}])

    def test_agent_query_passes_selected_model_to_all_openrouter_calls(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=[
                    '{"sql": "SELECT name, amount FROM donors", "rationale": "Find matching donors."}',
                    "Ada donated $100.00.",
                ],
            ) as mock_call:
                response = app.test_client().post(
                    "/api/agent/query",
                    json={
                        "question": "Who donated $100?",
                        "model": "openai/gpt-5.4",
                    },
                )
        finally:
            os.unlink(db_path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_call.call_count, 2)
        for call in mock_call.call_args_list:
            with self.subTest(call=call):
                self.assertEqual(call.kwargs["model"], "openai/gpt-5.4")

    def test_agent_query_rejects_unsupported_model(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=AssertionError("unsupported models should not reach OpenRouter"),
            ):
                response = app.test_client().post(
                    "/api/agent/query",
                    json={
                        "question": "Who donated $100?",
                        "model": "unknown/provider",
                    },
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("supported OpenRouter model", payload["error"])

    def test_agent_query_repairs_generated_sql_with_unknown_enum_value(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=[
                    json.dumps(
                        {
                            "sql": (
                                "SELECT COUNT(DISTINCT p.person_id) AS count "
                                "FROM persons p JOIN donors d ON LOWER(p.email) = LOWER(d.email) "
                                "WHERE LOWER(p.person_type) = 'staff'"
                            ),
                            "rationale": "Count staff members who are also donors.",
                        }
                    ),
                    json.dumps(
                        {
                            "sql": (
                                "SELECT COUNT(DISTINCT p.person_id) AS count "
                                "FROM persons p JOIN donors d ON LOWER(p.email) = LOWER(d.email)"
                            ),
                            "rationale": "Treat staff members as personnel records.",
                        }
                    ),
                    "1 staff member is also a donor.",
                ],
            ) as mock_call:
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "How many staff members are also donors?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_call.call_count, 3)
        self.assertNotIn("person_type", payload["sql"])
        self.assertEqual(payload["rows"], [{"count": 1}])
        repair_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("unsupported enum values", repair_prompt)
        self.assertIn("entity synonym 'staff'", repair_prompt)
        self.assertIn("interpret it as persons records", repair_prompt)

    def test_agent_query_repairs_personnel_entity_synonym_enum_filter(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
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

    def test_agent_query_retries_sql_generation_when_model_returns_non_json(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=[
                    "I would use SELECT name, amount FROM donors.",
                    '{"sql": "SELECT name, amount FROM donors", "rationale": "Find donor amounts."}',
                    "Ada donated $100.00.",
                ],
            ) as mock_call:
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "Who donated $100?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["answer"], "Ada donated $100.00.")
        self.assertEqual(mock_call.call_count, 3)
        repair_prompt = mock_call.call_args_list[1].args[0]
        self.assertIn("Previous model output", repair_prompt)
        self.assertIn("Return exactly one JSON object", repair_prompt)

    def test_agent_query_returns_stage_specific_timeout_error(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=TimeoutError("The read operation timed out"),
            ):
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "Who donated $100?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 504)
        self.assertIn("timed out", payload["error"])
        self.assertIn("generating SQL", payload["error"])
        self.assertNotIn("AI Agent failed", payload["error"])

    def test_agent_query_returns_stage_specific_remote_disconnect_error(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=RemoteDisconnected("Remote end closed connection without response"),
            ):
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "Who donated $100?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 502)
        self.assertIn("closed the connection", payload["error"])
        self.assertIn("generating SQL", payload["error"])
        self.assertNotIn("AI Agent failed", payload["error"])

    def test_agent_query_returns_stage_specific_openrouter_service_unavailable_error(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["OPENROUTER_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_openrouter",
                side_effect=agent_module.urlerror.HTTPError(
                    "https://openrouter.ai/api/v1/chat/completions",
                    503,
                    "Service Unavailable",
                    {},
                    None,
                ),
            ):
                response = app.test_client().post(
                    "/api/agent/query",
                    json={"question": "Who donated $100?"},
                )
        finally:
            os.unlink(db_path)

        payload = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertIn("HTTP 503", payload["error"])
        self.assertIn("Service Unavailable", payload["error"])
        self.assertIn("generating SQL", payload["error"])
        self.assertIn("temporary", payload["error"])
        self.assertIn("OPENROUTER_MODEL", payload["error"])
        self.assertNotIn("AI Agent failed", payload["error"])

    def test_agent_template_and_registration_hooks_exist(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")
        base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        app_py = (ROOT / "app.py").read_text(encoding="utf-8")

        for hook in [
            "agent-workspace",
            "agentQuestionForm",
            "agentModelSelect",
            "agentSqlTrace",
            "agentResultTable",
            "renderRows",
            "selectedModel",
            "JSON.stringify({question: text, model: selectedModel})",
        ]:
            self.assertIn(hook, template)
        self.assertNotIn("Result Preview", template)
        self.assertNotIn("return detail rows", template)
        self.assertLess(template.index('id="agentAnswerText"'), template.index('id="agentResultTable"'))
        self.assertIn("agent.agent_index", base)
        self.assertIn("from blueprints.agent import agent_bp", app_py)
        self.assertIn("app.register_blueprint(agent_bp)", app_py)

    def test_agent_recent_history_panel_hooks_exist(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

        for hook in [
            "agent-history-list",
            "agentHistoryList",
            "agentHistoryEmpty",
            "agentHistoryToggle",
            "agentHistoryBody",
            'aria-controls="agentHistoryBody"',
            'aria-expanded="true"',
            "agent-history-chevron",
            "agentQuestionDisplay",
            "agent-question-display",
            "Recent Questions",
            "Collapse recent questions",
            "Expand recent questions",
            "No recent questions yet.",
            "data-history-index",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, template)

    def test_agent_recent_history_uses_local_storage_and_limits_to_ten(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

        for hook in [
            "AGENT_HISTORY_KEY",
            "AGENT_HISTORY_COLLAPSED_KEY",
            "localStorage.getItem(AGENT_HISTORY_KEY)",
            "localStorage.setItem(AGENT_HISTORY_KEY",
            "localStorage.getItem(AGENT_HISTORY_COLLAPSED_KEY)",
            "localStorage.setItem(AGENT_HISTORY_COLLAPSED_KEY",
            "historyEntries.slice(0, 10)",
            "applyHistoryCollapsed(historyCollapsed)",
            "historyToggle.addEventListener('click'",
            "historyBody.hidden = collapsed",
            "saveHistoryEntry({",
            "renderHistory()",
            "showHistoryEntry(index)",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, template)

    def test_agent_answer_uses_controlled_markdown_renderer(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

        for hook in [
            "function renderMarkdownAnswer(text)",
            "const escaped = escapeHtml(text);",
            ".replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')",
            "function renderAnswer(text)",
            "answerText.innerHTML = renderMarkdownAnswer(text);",
            "renderAnswer(entry.answer || I18n.t('No answer returned.'))",
            "renderAnswer(I18n.t('Analyzing database...'))",
            "renderAnswer(answer)",
            "renderAnswer(err.message)",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, template)

        self.assertNotIn("answerText.textContent = answer", template)
        self.assertNotIn("answerText.textContent = err.message", template)

    def test_agent_starter_prompts_use_current_language(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")

        self.assertIn("data-prompt-zh", template)
        self.assertIn("I18n.getLang() === 'zh' ? btn.dataset.promptZh : btn.dataset.prompt", template)
        for prompt in [
            "哪些捐款人捐赠超过 500 美元，他们收到了哪些礼品？",
            "显示即将到来的排班，包括人员姓名和活动名称。",
            "哪些礼品当前库存最低？",
        ]:
            with self.subTest(prompt=prompt):
                self.assertIn(prompt, template)

    def test_agent_page_has_i18n_entries_and_dynamic_status_translation(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")
        i18n = (ROOT / "static" / "js" / "i18n.js").read_text(encoding="utf-8")

        expected_keys = [
            "AI Agent",
            "Ask questions across the full database.",
            "Read-only SQL",
            "Ask a database question to begin.",
            "The Agent creates a read-only lookup and answers from the returned data.",
            "Ask about donors, events, gifts, finance, schedules, or personnel...",
            "Analyzing database",
            "Ask Agent",
            "Agent Context",
            "Database scope",
            "All tables",
            "Read-only",
            "Row limit",
            "Latest SQL",
            "Result Table",
            "No query yet.",
            "No rows returned.",
            "row shown",
            "rows shown",
            "Waiting for generated SQL...",
            "Agent request failed.",
            "No answer returned.",
            "No SQL returned.",
            "Query was not executed.",
            "Recent Questions",
            "Collapse recent questions",
            "Expand recent questions",
            "No recent questions yet.",
            "Saved questions appear here after the Agent returns an answer.",
            "Saved",
        ]

        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(f"'{key}':", i18n)

        for dynamic_key in [
            "No query yet.",
            "No rows returned.",
            "Analyzing database...",
            "Waiting for generated SQL...",
            "Agent request failed.",
            "No answer returned.",
            "No SQL returned.",
            "Query was not executed.",
            "Collapse recent questions",
            "Expand recent questions",
        ]:
            with self.subTest(dynamic_key=dynamic_key):
                self.assertIn(f"I18n.t('{dynamic_key}')", template)

    def _make_temp_app(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = handle.name
        handle.close()
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE donors ("
            "donor_id INTEGER PRIMARY KEY, name TEXT, amount REAL, email TEXT)"
        )
        conn.execute(
            "CREATE TABLE persons ("
            "person_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, "
            "email TEXT, person_type TEXT, role_name TEXT, status TEXT)"
        )
        conn.execute(
            "INSERT INTO donors (name, amount, email) VALUES "
            "('Ada', 100.0, 'ada@example.org')"
        )
        conn.execute(
            "INSERT INTO persons "
            "(first_name, last_name, email, person_type, role_name, status) VALUES "
            "('Ada', 'Lovelace', 'ada@example.org', 'Employee', 'Coordinator', 'active')"
        )
        conn.execute(
            "INSERT INTO persons "
            "(first_name, last_name, email, person_type, role_name, status) VALUES "
            "('Grace', 'Hopper', 'grace@example.org', 'Volunteer', 'Driver', 'active')"
        )
        conn.commit()
        conn.close()

        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            DATABASE=db_path,
            OPENROUTER_API_KEY="",
            OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
            OPENROUTER_MODEL="anthropic/claude-sonnet-4.6",
            AGENT_ROW_LIMIT=50,
            LOGIN_DISABLED=True,
        )
        init_app(app)
        return app, db_path


if __name__ == "__main__":
    unittest.main()
