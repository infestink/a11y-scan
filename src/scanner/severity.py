from __future__ import annotations

from src.api.models import Severity

# Explicit overrides for specific axe rule IDs that warrant promotion/demotion
# relative to their default impact level.
_RULE_OVERRIDES: dict[str, Severity] = {
    # Always critical — keyboard traps prevent any further interaction
    "scrollable-region-focusable": Severity.critical,
    "keyboard": Severity.critical,
    # Promote to serious — colour contrast failures are serious usability barriers
    "color-contrast": Severity.serious,
    "color-contrast-enhanced": Severity.serious,
    # Common informational/advisory items
    "region": Severity.advisory,
    "landmark-one-main": Severity.advisory,
    "page-has-heading-one": Severity.advisory,
    "bypass": Severity.advisory,
    "skip-link": Severity.advisory,
}

# axe impact -> default severity when no rule override applies
_IMPACT_MAP: dict[str, Severity] = {
    "critical": Severity.critical,
    "serious": Severity.serious,
    "moderate": Severity.advisory,
    "minor": Severity.advisory,
}


def map_severity(rule_id: str, impact: str) -> Severity:
    """Return the a11y-scan severity for a given axe rule + impact pair."""
    if rule_id in _RULE_OVERRIDES:
        return _RULE_OVERRIDES[rule_id]
    return _IMPACT_MAP.get(impact.lower(), Severity.advisory)
