from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PERSONS_TEMPLATE = ROOT / "templates" / "personnel" / "persons.html"
DONORS_TEMPLATE = ROOT / "templates" / "donations" / "donors.html"
PERSONNEL_BP = ROOT / "blueprints" / "personnel.py"
DONATIONS_BP = ROOT / "blueprints" / "donations.py"
I18N_JS = ROOT / "static" / "js" / "i18n.js"


class MaritalStatusUiTests(unittest.TestCase):
    def test_persons_page_exposes_marital_status_in_table_and_form(self):
        text = PERSONS_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            'data-i18n="Marital Status"',
            'name="marital_status"',
            'id="marital_status"',
            "p['marital_status']",
            "function openEdit(id, first_name, last_name, email, phone, person_type, role_name, hire_date, status, birthday, gender, marital_status)",
            "document.getElementById('marital_status').value = marital_status;",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_donors_page_exposes_marital_status_in_table_and_form(self):
        text = DONORS_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            'data-i18n="Marital Status"',
            "d.marital_status",
            'name="marital_status"',
            'id="marital_status"',
            "function openEditModal(id, type, firstName, lastName, email, age, gender, location, maritalStatus)",
            "document.getElementById('marital_status').value = maritalStatus;",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_persons_and_donors_crud_persist_marital_status(self):
        personnel = PERSONNEL_BP.read_text(encoding="utf-8")
        donations = DONATIONS_BP.read_text(encoding="utf-8")

        for hook in [
            "gender, marital_status, created_date",
            "birthday=?, gender=?, marital_status=?",
            "request.form.get('marital_status', 'Unknown')",
            "UPDATE donors SET marital_status=?",
        ]:
            with self.subTest(file="personnel.py", hook=hook):
                self.assertIn(hook, personnel)

        for hook in [
            "gender, location, marital_status, created_date",
            "gender=?, location=?, marital_status=?",
            "request.form.get('marital_status', 'Unknown')",
            "UPDATE persons SET marital_status=?",
        ]:
            with self.subTest(file="donations.py", hook=hook):
                self.assertIn(hook, donations)

    def test_i18n_has_marital_status_keys_and_values(self):
        text = I18N_JS.read_text(encoding="utf-8")

        for key in [
            "Marital Status",
            "Married",
            "Single",
            "Divorced",
            "Widowed",
            "Unknown",
        ]:
            with self.subTest(key=key):
                self.assertIn(f"'{key}':", text)


if __name__ == "__main__":
    unittest.main()
