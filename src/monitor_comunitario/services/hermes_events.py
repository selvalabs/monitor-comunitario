import json
from typing import Any

from sqlalchemy.orm import Session

from monitor_comunitario.db.models import HermesEvent, HermesEventStatus
from monitor_comunitario.services.hermes_catalog import get_template


def create_hermes_event(
    *,
    session: Session,
    event_type: str,
    channel: str,
    recipient_phone: str,
    intent: str,
    template_key: str,
    payload: dict[str, Any],
    source: str = "monitor_comunitario",
    llm_allowed: bool = False,
) -> HermesEvent:
    """Persist one auditable Hermes event without external delivery."""
    template = get_template(template_key)

    if template.user_facing and llm_allowed:
        raise ValueError("LLM is not allowed for user-facing Hermes templates.")

    event = HermesEvent(
        event_type=event_type,
        status=HermesEventStatus.CREATED.value,
        source=source,
        channel=channel,
        recipient_phone=recipient_phone,
        intent=intent,
        template_key=template_key,
        payload_json=json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True),
        llm_allowed=llm_allowed,
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event
