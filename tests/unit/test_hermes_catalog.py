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


def test_registration_confirmation_templates_explain_the_next_step() -> None:
    confirmation = get_template("member_phone_confirmation_v1")
    completion = get_template("member_access_code_v1")

    assert (
        "Você quer receber avisos de desligamentos programados e falta de energia para o "
        "endereço cadastrado?" in confirmation.body
    )
    assert "Responda *OK* para confirmar." in confirmation.body
    assert "Responda *CANCELAR* para encerrar o cadastro." in confirmation.body
    assert "Esta confirmação vale por {phone_confirmation_ttl_hours} horas." in confirmation.body
    assert "\n\n" in confirmation.body
    assert "Cadastro confirmado, {name}." in completion.body
    assert "Seu código de acesso: *{access_code}*" in completion.body
    assert "responda *PARAR*." in completion.body
    assert "\n\n" in completion.body
