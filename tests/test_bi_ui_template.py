from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BI_TEMPLATE = ROOT / "templates" / "bi" / "index.html"
I18N_JS = ROOT / "static" / "js" / "i18n.js"


def _template_text():
    return BI_TEMPLATE.read_text(encoding="utf-8")


def _i18n_text():
    return I18N_JS.read_text(encoding="utf-8")


class BiUiTemplateTests(unittest.TestCase):
    def test_bi_results_put_chart_before_table_for_decision_first_flow(self):
        text = _template_text()

        self.assertIn('id="biInsightPanel"', text)
        self.assertLess(text.index('id="biChartWrap"'), text.index('id="biResults"'))

    def test_bi_presets_are_business_questions_not_short_labels(self):
        text = _template_text()

        expected_questions = [
            "Which donation channel brings the most value?",
            "Where are donors concentrated?",
            "Which events are closest to target?",
            "Which gifts are moving fastest?",
            "How is attendance trending?",
        ]
        for question in expected_questions:
            self.assertIn(question, text)

        self.assertIn("question:", text)
        self.assertIn("primaryMetric: 'achievement_rate'", text)

    def test_bi_builder_uses_domain_aware_guidance_copy(self):
        text = _template_text()

        self.assertIn("const DOMAIN_GUIDANCE", text)
        self.assertIn('id="filterHelp"', text)
        self.assertIn('id="dimensionHelp"', text)
        self.assertIn('id="metricHelp"', text)
        self.assertNotIn("Which people to include", text)

    def test_bi_visual_polish_is_scoped_and_reduces_heavy_builder_cards(self):
        text = _template_text()

        self.assertIn("bi-workspace-header", text)
        self.assertIn("bi-question-select", text)
        self.assertIn('id="businessQuestionSelect"', text)
        self.assertIn("bi-analysis-shell", text)
        self.assertIn("bi-control-rail", text)
        self.assertIn("bi-output-workspace", text)
        self.assertIn("minmax(320px, 400px) minmax(0, 1fr)", text)
        self.assertIn('"controls output"', text)
        self.assertIn("bi-builder-stack", text)
        self.assertNotIn("bi-preset-pill", text)
        self.assertNotIn('id="presetContainer"', text)
        self.assertIn("grid-template-areas", text)
        self.assertIn('"filters"', text)
        self.assertIn('"dimensions"', text)
        self.assertIn('"metrics"', text)
        self.assertIn("bi-builder-card", text)
        self.assertIn("bi-result-stack", text)
        self.assertNotIn("border:2px solid var(--accent);background:var(--bg-card);box-shadow:var(--shadow-md);overflow:hidden;", text)

    def test_bi_new_copy_has_i18n_keys(self):
        text = _i18n_text()

        for key in [
            "Analytics Workspace",
            "Question-led analysis across 6 domains",
            "Business Questions",
            "Select a business question",
            "Choose measures to compare",
        ]:
            self.assertIn(key, text)

    def test_bi_balanced_workspace_has_result_layers(self):
        text = _template_text()

        expected_hooks = [
            "bi-insight-strip",
            "bi-insight-item",
            "bi-chart-workspace",
            "bi-chart-toolbar",
            "bi-table-shell",
            "bi-table-scroll",
        ]
        for hook in expected_hooks:
            self.assertIn(hook, text)

        self.assertLess(text.index('id="biInsightPanel"'), text.index('id="biChartWrap"'))
        self.assertLess(text.index('id="biChartWrap"'), text.index('id="biResults"'))

    def test_bi_mobile_and_table_polish_hooks_exist(self):
        text = _template_text()

        expected_css = [
            ".bi-chart-workspace",
            ".bi-chart-toolbar",
            ".bi-table-shell",
            ".bi-table-scroll",
            ".bi-output-workspace",
            "@media (max-width: 767.98px)",
        ]
        for css in expected_css:
            self.assertIn(css, text)


if __name__ == "__main__":
    unittest.main()
