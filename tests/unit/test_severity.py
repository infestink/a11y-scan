import pytest

from src.api.models import Severity
from src.scanner.severity import map_severity


@pytest.mark.unit
class TestMapSeverity:
    def test_impact_critical(self):
        assert map_severity("unknown-rule", "critical") == Severity.critical

    def test_impact_serious(self):
        assert map_severity("unknown-rule", "serious") == Severity.serious

    def test_impact_moderate(self):
        assert map_severity("unknown-rule", "moderate") == Severity.advisory

    def test_impact_minor(self):
        assert map_severity("unknown-rule", "minor") == Severity.advisory

    def test_unknown_impact_defaults_advisory(self):
        assert map_severity("unknown-rule", "bogus") == Severity.advisory

    def test_rule_override_keyboard(self):
        # keyboard trap always critical regardless of passed impact
        assert map_severity("keyboard", "moderate") == Severity.critical

    def test_rule_override_color_contrast(self):
        assert map_severity("color-contrast", "moderate") == Severity.serious

    def test_rule_override_region(self):
        assert map_severity("region", "critical") == Severity.advisory

    @pytest.mark.parametrize("rule", ["landmark-one-main", "page-has-heading-one", "bypass"])
    def test_advisory_overrides(self, rule):
        assert map_severity(rule, "serious") == Severity.advisory
