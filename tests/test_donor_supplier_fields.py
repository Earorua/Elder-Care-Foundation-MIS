from pathlib import Path
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "elder_care.db"
DONORS_TEMPLATE = ROOT / "templates" / "donations" / "donors.html"
SUPPLIERS_TEMPLATE = ROOT / "templates" / "gifts" / "suppliers.html"
DONATIONS_BP = ROOT / "blueprints" / "donations.py"
GIFTS_BP = ROOT / "blueprints" / "gifts.py"
I18N_JS = ROOT / "static" / "js" / "i18n.js"


def db_rows(sql, args=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


class DonorSupplierFieldTests(unittest.TestCase):
    def test_database_has_donor_type_column_and_valid_values(self):
        donor_columns = {row["name"] for row in db_rows("PRAGMA table_info(donors)")}

        self.assertIn("type", donor_columns)
        self.assertEqual(
            [],
            [
                dict(row)
                for row in db_rows(
                    "SELECT donor_id, type FROM donors "
                    "WHERE type IS NULL OR type NOT IN ('Person', 'Company')"
                )
            ],
        )

    def test_database_has_supplier_contact_email_values(self):
        supplier_columns = {row["name"] for row in db_rows("PRAGMA table_info(suppliers)")}
        rows = db_rows("SELECT supplier_name, contact_email FROM suppliers ORDER BY supplier_id")
        emails = {row["supplier_name"]: row["contact_email"] for row in rows}

        self.assertIn("contact_email", supplier_columns)
        self.assertEqual(
            {
                "Pacific Print House": "keoni.nakamura@pacificprinthouse.org",
                "Buck Steel Illustrations": "buck.steel@steelartstudio.org",
                "Sunrise Animation Studio": "amy.chen@sunriseanimationstudio.org",
                "Campus Copy & Design": "jordan.lee@campuscopydesign.org",
            },
            emails,
        )

    def test_donor_template_exposes_type_column_and_type_only_dropdown(self):
        text = DONORS_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            'data-i18n="Donor Type"',
            "i18n_value(d.type)",
            'name="type"',
            'id="type"',
            '<option value="Person" data-i18n="Person">Person</option>',
            '<option value="Company" data-i18n="Company">Company</option>',
            "function openEditModal(id, type, firstName, lastName, email, age, gender, location, maritalStatus)",
            "document.getElementById('type').value = type;",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_donor_crud_persists_type_field(self):
        text = DONATIONS_BP.read_text(encoding="utf-8")

        for hook in [
            "INSERT INTO donors (type, first_name, last_name, email, age, gender, location, marital_status, created_date)",
            "request.form.get('type', 'Person')",
            "UPDATE donors SET type=?, first_name=?, last_name=?, email=?, age=?, gender=?, location=?, marital_status=?",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_supplier_template_exposes_contact_email_column_and_form_field(self):
        text = SUPPLIERS_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            'data-i18n="Contact Email"',
            "r.contact_email",
            'name="contact_email"',
            'id="f_contact_email"',
            "function openEdit(id,name,address,phone,company,contact,email)",
            "document.getElementById('f_contact_email').value=email;",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_supplier_crud_persists_contact_email_field(self):
        text = GIFTS_BP.read_text(encoding="utf-8")

        for hook in [
            "INSERT INTO suppliers (supplier_name, address, phone, company, contact_name, contact_email) VALUES (?,?,?,?,?,?)",
            "request.form.get('contact_email', '')",
            "UPDATE suppliers SET supplier_name=?, address=?, phone=?, company=?, contact_name=?, contact_email=? WHERE supplier_id=?",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

    def test_i18n_has_new_field_and_option_labels(self):
        text = I18N_JS.read_text(encoding="utf-8")

        for key in ["Donor Type", "Contact Email", "Person", "Company"]:
            with self.subTest(key=key):
                self.assertIn(f"'{key}':", text)


if __name__ == "__main__":
    unittest.main()
