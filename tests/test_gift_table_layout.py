from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GIFTS_TEMPLATE = ROOT / "templates" / "gifts" / "gifts.html"
STYLE_CSS = ROOT / "static" / "css" / "style.css"


class GiftTableLayoutTests(unittest.TestCase):
    def test_description_column_has_language_independent_width(self):
        template = GIFTS_TEMPLATE.read_text(encoding="utf-8")
        css = STYLE_CSS.read_text(encoding="utf-8")

        self.assertIn('table class="table table-striped table-hover align-middle gift-inventory-table"', template)
        self.assertIn('<th class="gift-description-column" data-i18n="Description">Description</th>', template)
        self.assertIn('<td class="gift-description-column" title="{{ r.description }}">{{ r.description }}</td>', template)

        self.assertIn(".gift-inventory-table .gift-description-column", css)
        for hook in [
            "width: 18rem;",
            "min-width: 18rem;",
            "max-width: 18rem;",
            "overflow-wrap: anywhere;",
        ]:
            with self.subTest(hook=hook):
                self.assertIn(hook, css)


if __name__ == "__main__":
    unittest.main()
