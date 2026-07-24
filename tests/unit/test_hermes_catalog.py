from monitor_comunitario.services.hermes_catalog import (
    HERMES_ESCALATION_EVENTS,
    HERMES_EVENT_TYPES,
    HERMES_TEMPLATES,
    UserFacingIntent,
    get_template,
)


def test_user_facing_intents_include_issue_37_initial_scope() -> None:
    assert UserFacingIntent.HELP.value == "HELP"
    assert UserFacingIntent.DELETE_DATA_REQUEST.value == "DELETE_DATA_REQUEST"
    assert UserFacingIntent.UNKNOWN_ESCALATE.value == "UNKNOWN_ESCALATE"


def test_templates_are_deterministic_and_versioned() -> None:
    template = get_template("alert_explanation_v1")

    assert template.intent == UserFacingIntent.ALERT_EXPLANATION
    assert template.user_facing is True
    assert template.llm_allowed is False
    assert "{municipality}" in template.body


def test_catalog_contains_operational_event_types() -> None:
    assert "notification_ready" in HERMES_EVENT_TYPES
    assert "scraper_failed" in HERMES_ESCALATION_EVENTS
    assert "human_escalation_v1" in HERMES_TEMPLATES
