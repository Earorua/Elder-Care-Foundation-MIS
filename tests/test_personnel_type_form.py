from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PERSONS_TEMPLATE = ROOT / "templates" / "personnel" / "persons.html"


class PersonnelTypeFormTests(unittest.TestCase):
    def test_person_type_form_control_is_employee_volunteer_select(self):
        text = PERSONS_TEMPLATE.read_text(encoding="utf-8")

        for hook in [
            '<select class="form-select" name="person_type" id="person_type">',
            '<option value="Employee" data-i18n="Employee">Employee</option>',
            '<option value="Volunteer" data-i18n="Volunteer">Volunteer</option>',
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, text)

        self.assertNotIn(
            '<input type="text" class="form-control" name="person_type" id="person_type">',
            text,
        )
        self.assertIn(
            '<input type="text" class="form-control" name="role_name" id="role_name">',
            text,
        )


if __name__ == "__main__":
    unittest.main()
