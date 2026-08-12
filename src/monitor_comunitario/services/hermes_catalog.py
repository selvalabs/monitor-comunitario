from dataclasses import dataclass
from enum import StrEnum


class UserFacingIntent(StrEnum):
    """Deterministic support intents allowed for resident-facing flows."""

    HELP = "HELP"
    WHAT_IS_THIS = "WHAT_IS_THIS"
    NOT_CELESC = "NOT_CELESC"
    ALERT_EXPLANATION = "ALERT_EXPLANATION"
    ACCESS_MEMBER_AREA = "ACCESS_MEMBER_AREA"
    LOST_ACCESS_CODE = "LOST_ACCESS_CODE"
    UPDATE_ADDRESS = "UPDATE_ADDRESS"
    OPT_OUT = "OPT_OUT"
    DELETE_DATA_REQUEST = "DELETE_DATA_REQUEST"
    WRONG_ALERT_FEEDBACK = "WRONG_ALERT_FEEDBACK"
    EMERGENCY = "EMERGENCY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN_ESCALATE = "UNKNOWN_ESCALATE"


@dataclass(frozen=True)
class HermesTemplate:
    """Approved deterministic template metadata."""

    key: str
    intent: UserFacingIntent
    body: str
    user_facing: bool = True
    llm_allowed: bool = False


HERMES_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "notification_ready",
        "admin_approval_pending",
        "member_phone_confirmation_requested",
        "member_phone_confirmation_completed",
        "support_message_received",
        "support_response_ready",
        "admin_summary_requested",
        "scraper_failed",
        "parser_failed",
        "worker_failed",
        "notification_delivery_failed",
        "gateway_down",
    }
)

HERMES_ESCALATION_EVENTS: frozenset[str] = frozenset(
    {
        "scraper_failed",
        "parser_failed",
        "worker_failed",
        "zero_notices_unusual",
        "many_uncertain_matches",
        "notification_delivery_failed",
        "admin_approval_pending",
        "user_requested_removal",
        "user_reported_wrong_alert",
        "user_support_needs_human",
        "privacy_sensitive_request",
        "gateway_down",
    }
)

HERMES_TEMPLATES: dict[str, HermesTemplate] = {
    "explain_project_v1": HermesTemplate(
        key="explain_project_v1",
        intent=UserFacingIntent.WHAT_IS_THIS,
        body=(
            "O Monitor Comunitario usa avisos publicos da Celesc para indicar quando "
            "um desligamento programado pode afetar o endereco cadastrado."
        ),
    ),
    "not_official_celesc_v1": HermesTemplate(
        key="not_official_celesc_v1",
        intent=UserFacingIntent.NOT_CELESC,
        body=(
            "Este projeto nao e um canal oficial da Celesc. Confira os canais oficiais "
            "antes de tomar decisoes importantes."
        ),
    ),
    "alert_explanation_v1": HermesTemplate(
        key="alert_explanation_v1",
        intent=UserFacingIntent.ALERT_EXPLANATION,
        body=(
            "Encontramos um aviso publico de desligamento em {municipality}. "
            "A area informada foi {area}. O alerta e probabilistico."
        ),
    ),
    "member_access_help_v1": HermesTemplate(
        key="member_access_help_v1",
        intent=UserFacingIntent.ACCESS_MEMBER_AREA,
        body="Acesse a area do morador com seu telefone e codigo privado.",
    ),
    "lost_code_help_v1": HermesTemplate(
        key="lost_code_help_v1",
        intent=UserFacingIntent.LOST_ACCESS_CODE,
        body=(
            "Por seguranca, o codigo privado nao e exibido novamente. Solicite suporte "
            "humano para revisar o cadastro."
        ),
    ),
    "update_address_help_v1": HermesTemplate(
        key="update_address_help_v1",
        intent=UserFacingIntent.UPDATE_ADDRESS,
        body="Para atualizar endereco, acesse a area do morador ou solicite suporte.",
    ),
    "opt_out_received_v1": HermesTemplate(
        key="opt_out_received_v1",
        intent=UserFacingIntent.OPT_OUT,
        body="Recebemos seu pedido para parar alertas. O operador vai processar a solicitacao.",
    ),
    "delete_data_request_received_v1": HermesTemplate(
        key="delete_data_request_received_v1",
        intent=UserFacingIntent.DELETE_DATA_REQUEST,
        body="Recebemos seu pedido de exclusao de dados e ele sera encaminhado ao operador.",
    ),
    "wrong_alert_feedback_received_v1": HermesTemplate(
        key="wrong_alert_feedback_received_v1",
        intent=UserFacingIntent.WRONG_ALERT_FEEDBACK,
        body="Obrigado pelo aviso. Vamos registrar que este alerta pode estar incorreto.",
    ),
    "emergency_redirect_v1": HermesTemplate(
        key="emergency_redirect_v1",
        intent=UserFacingIntent.EMERGENCY,
        body=(
            "Este projeto nao cobre emergencia. Em falta de energia ou risco imediato, "
            "use os canais oficiais da Celesc e servicos de emergencia."
        ),
    ),
    "out_of_scope_v1": HermesTemplate(
        key="out_of_scope_v1",
        intent=UserFacingIntent.OUT_OF_SCOPE,
        body=(
            "Nao consigo ajudar com esse assunto por aqui. "
            "Vou limitar a resposta ao escopo do projeto."
        ),
    ),
    "member_phone_confirmation_v1": HermesTemplate(
        key="member_phone_confirmation_v1",
        intent=UserFacingIntent.ACCESS_MEMBER_AREA,
        body=(
            "Oi, {name}.\n\n"
            "Você quer receber avisos de desligamentos programados e falta de energia para o "
            "endereço cadastrado?\n\n"
            "Responda *OK* para confirmar.\n"
            "Responda *CANCELAR* para encerrar o cadastro.\n\n"
            "Esta confirmação vale por {phone_confirmation_ttl_hours} horas.\n"
            "Saiba mais: {url}"
        ),
    ),
    "member_access_code_v1": HermesTemplate(
        key="member_access_code_v1",
        intent=UserFacingIntent.ACCESS_MEMBER_AREA,
        body=(
            "Cadastro confirmado, {name}.\n\n"
            "Você receberá avisos de desligamentos programados para o endereço cadastrado.\n\n"
            "Seu código de acesso: *{access_code}*\n"
            "Acesse sua área: {url}\n\n"
            "Para parar de receber avisos a qualquer momento, responda *PARAR*."
        ),
    ),
    "human_escalation_v1": HermesTemplate(
        key="human_escalation_v1",
        intent=UserFacingIntent.UNKNOWN_ESCALATE,
        body="Sua mensagem sera encaminhada para revisao humana.",
    ),
}


def get_template(template_key: str) -> HermesTemplate:
    """Return an approved Hermes template by key."""
    return HERMES_TEMPLATES[template_key]
