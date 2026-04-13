import os
import sqlite3
import tempfile
import unittest
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import patch

import config
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
    def test_default_siliconflow_model_is_requested_model(self):
        expected_model = "Pro/zai-org/GLM-5.1"
        agent_py = (ROOT / "blueprints" / "agent.py").read_text(encoding="utf-8")

        self.assertEqual(config.SILICONFLOW_MODEL, expected_model)
        self.assertIn(expected_model, agent_py)

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

    def test_agent_query_returns_setup_error_when_api_key_missing(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["SILICONFLOW_API_KEY"] = ""
        try:
            response = app.test_client().post("/api/agent/query", json={"question": "How many donors?"})
        finally:
            os.unlink(db_path)

        self.assertEqual(response.status_code, 400)
        self.assertIn("SILICONFLOW_API_KEY", response.get_json()["error"])

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
        app.config["SILICONFLOW_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_siliconflow",
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

    def test_agent_query_retries_sql_generation_when_model_returns_non_json(self):
        app, db_path = self._make_temp_app()
        app.register_blueprint(agent_bp)
        app.config["SILICONFLOW_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_siliconflow",
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
        app.config["SILICONFLOW_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_siliconflow",
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
        app.config["SILICONFLOW_API_KEY"] = "test-key"
        try:
            with patch(
                "blueprints.agent._call_siliconflow",
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

    def test_agent_template_and_registration_hooks_exist(self):
        template = (ROOT / "templates" / "agent" / "index.html").read_text(encoding="utf-8")
        base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        app_py = (ROOT / "app.py").read_text(encoding="utf-8")

        for hook in [
            "agent-workspace",
            "agentQuestionForm",
            "agentSqlTrace",
            "agentResultTable",
            "renderRows",
        ]:
            self.assertIn(hook, template)
        self.assertNotIn("Result Preview", template)
        self.assertNotIn("return detail rows", template)
        self.assertLess(template.index('id="agentAnswerText"'), template.index('id="agentResultTable"'))
        self.assertIn("agent.agent_index", base)
        self.assertIn("from blueprints.agent import agent_bp", app_py)
        self.assertIn("app.register_blueprint(agent_bp)", app_py)

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
        ]:
            with self.subTest(dynamic_key=dynamic_key):
                self.assertIn(f"I18n.t('{dynamic_key}')", template)

    def _make_temp_app(self):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = handle.name
        handle.close()
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE donors (donor_id INTEGER PRIMARY KEY, name TEXT, amount REAL)")
        conn.execute("INSERT INTO donors (name, amount) VALUES ('Ada', 100.0)")
        conn.commit()
        conn.close()

        app = Flask(__name__)
        app.config.update(
            TESTING=True,
            DATABASE=db_path,
            SILICONFLOW_API_KEY="",
            SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1",
            SILICONFLOW_MODEL="Pro/zai-org/GLM-5.1",
            AGENT_ROW_LIMIT=50,
            LOGIN_DISABLED=True,
        )
        init_app(app)
        return app, db_path


if __name__ == "__main__":
    unittest.main()
