from pathlib import Path
import unittest

from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
I18N_JS = ROOT / "static" / "js" / "i18n.js"


def read_template(relative_path):
    return (TEMPLATES / relative_path).read_text(encoding="utf-8")


class TableFixedValueI18nTests(unittest.TestCase):
    def test_value_macro_renders_data_i18n_span(self):
        env = Environment(
            loader=FileSystemLoader(TEMPLATES),
            autoescape=select_autoescape(["html"]),
        )
        template = env.from_string(
            '{% from "macros/i18n_values.html" import value %}'
            '{{ value("Male") }}{{ value(None) }}'
        )

        rendered = template.render()

        self.assertIn('<span data-i18n="Male">Male</span>', rendered)
        self.assertNotIn("None", rendered)

    def test_representative_server_templates_wrap_fixed_values(self):
        expectations = {
            "donations/donations.html": [
                "i18n_value(d.donation_type)",
                'i18n_value("Yes" if d.is_tax_deductible else "No")',
            ],
            "donations/donors.html": [
                "i18n_value(d.gender)",
                "i18n_value(d.marital_status)",
            ],
            "personnel/persons.html": [
                "i18n_value(p['person_type'])",
                "i18n_value(p['gender'])",
                "i18n_value(p['marital_status'])",
                "i18n_value(p['status'])",
            ],
            "auth/users.html": [
                "{'admin': 'Admin'",
                "'event_coordinator': 'Event Coordinator'",
                "i18n_value(role_labels.get(u.role, u.role))",
            ],
            "gifts/distribution.html": [
                "#{{ r.batch_id }} ({{ i18n_value(r.batch_type) }})",
                "i18n_value('Yes' if r.is_free == 1 else 'No')",
                "i18n_value(r.distribution_reason)",
            ],
            "gifts/delivery.html": [
                "i18n_value(r.delivery_status)",
            ],
            "events/events.html": [
                "i18n_value(e.event_type)",
                "i18n_value(e.status)",
            ],
            "finance/income_statement.html": [
                "i18n_value(r.donation_type)",
                "i18n_value(r.income_type)",
                "i18n_value(r.payment_type)",
            ],
            "finance/expenditure.html": [
                "{{ i18n_value(r.payment_type) }} <small",
            ],
        }

        for relative_path, hooks in expectations.items():
            text = read_template(relative_path)
            with self.subTest(template=relative_path):
                self.assertIn("import value as i18n_value", text)
            for hook in hooks:
                with self.subTest(template=relative_path, hook=hook):
                    self.assertIn(hook, text)

    def test_target_templates_no_obvious_bare_table_outputs(self):
        forbidden = {
            "donations/donations.html": [
                "<td>{{ d.donation_type }}</td>",
                '<td>{{ "Yes" if d.is_tax_deductible else "No" }}</td>',
            ],
            "personnel/persons.html": [
                "<td>{{ p['person_type'] }}</td>",
                "<td>{{ p['gender'] }}</td>",
                "<td>{{ p['status'] }}</td>",
            ],
            "gifts/distribution.html": [
                "<td>#{{ r.batch_id }} ({{ r.batch_type }})</td>",
                "<td>{{ 'Yes' if r.is_free == 1 else 'No' }}</td>",
            ],
            "gifts/delivery.html": [
                "<td>{{ r.delivery_status }}</td>",
            ],
        }

        for relative_path, hooks in forbidden.items():
            text = read_template(relative_path)
            for hook in hooks:
                with self.subTest(template=relative_path, hook=hook):
                    self.assertNotIn(hook, text)

    def test_open_text_table_values_remain_untranslated(self):
        expectations = {
            "personnel/persons.html": [
                "<td>{{ p['role_name'] }}</td>",
                "i18n_value(p['role_name'])",
            ],
            "gifts/gifts.html": [
                "<td>{{ r.gift_type }}</td>",
                "i18n_value(r.gift_type)",
            ],
        }

        for relative_path, (bare_output, wrapped_output) in expectations.items():
            text = read_template(relative_path)
            with self.subTest(template=relative_path, hook=bare_output):
                self.assertIn(bare_output, text)
            with self.subTest(template=relative_path, hook=wrapped_output):
                self.assertNotIn(wrapped_output, text)

    def test_schedule_board_uses_value_helper_for_client_rendered_fixed_values(self):
        text = read_template("personnel/schedule_board.html")

        for hook in [
            "I18n.value('Absent')",
            "I18n.value('On Time')",
            "I18n.value('On Duty')",
            "I18n.value(item.role_name",
            "I18n.value(item.schedule_type",
            "I18n.value(label)",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_i18n_value_helper_and_fixed_option_keys_exist(self):
        text = I18N_JS.read_text(encoding="utf-8")

        for hook in [
            "const VALUE_KEY_MAP = {",
            "function value(key) {",
            "global.I18n = { t, value, setLang, getLang, applyAll };",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

        for key in [
            "Male",
            "Female",
            "Employee",
            "Volunteer",
            "Cash",
            "Check",
            "Wire Transfer",
            "Salary",
            "Bonus",
            "active",
            "inactive",
            "Planned",
            "Completed",
            "Scheduled",
            "Delivered",
            "In Transit",
            "Positive",
            "Suggestion",
            "Reviewed",
            "Physical",
            "Digital",
            "Admin",
            "Event Coordinator",
            "Viewer",
        ]:
            with self.subTest(key=key):
                self.assertIn(f"'{key}':", text)


if __name__ == "__main__":
    unittest.main()
