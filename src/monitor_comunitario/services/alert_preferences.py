from collections.abc import Mapping
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import OutageNotice, UserAlertPreference


class AlertSource(StrEnum):
    CELESC_SCHEDULED = "celesc_scheduled"
    CELESC_EMERGENCY = "celesc_emergency"
    CASAN_WATER = "casan_water"
    DEFESA_CIVIL_SC = "defesa_civil_sc"


DEFAULT_ALERT_PREFERENCES: dict[str, bool] = {
    AlertSource.CELESC_SCHEDULED.value: True,
    AlertSource.CELESC_EMERGENCY.value: True,
    AlertSource.CASAN_WATER.value: True,
    AlertSource.DEFESA_CIVIL_SC.value: False,
}


def notice_alert_source(notice: OutageNotice) -> str | None:
    """Map a persisted notice to the resident preference key."""
    if notice.source == "celesc" and notice.notice_type == "scheduled":
        return AlertSource.CELESC_SCHEDULED.value
    if notice.source == "celesc-emergency" or notice.notice_type == "emergency":
        return AlertSource.CELESC_EMERGENCY.value
    if notice.source == "casan" or notice.notice_type == "water":
        return AlertSource.CASAN_WATER.value
    if notice.source == "defesa-civil-sc":
        return AlertSource.DEFESA_CIVIL_SC.value
    return None


def get_user_alert_preferences(session: Session, user_id: int) -> dict[str, bool]:
    """Return explicit preferences over safe, backward-compatible defaults."""
    preferences = dict(DEFAULT_ALERT_PREFERENCES)
    rows = session.scalars(
        select(UserAlertPreference).where(UserAlertPreference.user_id == user_id)
    ).all()
    preferences.update({row.source_key: row.enabled for row in rows})
    return preferences


def save_user_alert_preferences(
    session: Session,
    user_id: int,
    preferences: Mapping[str, bool],
) -> dict[str, bool]:
    """Upsert known source preferences and return the complete effective set."""
    allowed_keys = set(DEFAULT_ALERT_PREFERENCES)
    normalized = {
        key: bool(value) for key, value in preferences.items() if key in allowed_keys
    }
    existing = {
        row.source_key: row
        for row in session.scalars(
            select(UserAlertPreference).where(UserAlertPreference.user_id == user_id)
        ).all()
    }
    for key, enabled in normalized.items():
        row = existing.get(key)
        if row is None:
            session.add(
                UserAlertPreference(user_id=user_id, source_key=key, enabled=enabled)
            )
        else:
            row.enabled = enabled
    session.flush()
    return get_user_alert_preferences(session, user_id)


def user_accepts_notice(
    session: Session,
    user_id: int,
    notice: OutageNotice,
) -> bool:
    """Return whether the user opted into this notice's source."""
    source_key = notice_alert_source(notice)
    if source_key is None:
        return False
    return get_user_alert_preferences(session, user_id).get(source_key, False)
