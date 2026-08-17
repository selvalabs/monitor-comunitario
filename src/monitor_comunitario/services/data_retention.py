import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import (
    HermesEvent,
    Notification,
    User,
    UserAlertPreference,
    UserOutageMatch,
)


def purge_user_data(session: Session, user: User) -> None:
    """Remove personal and derived records belonging to one user."""
    for event in session.scalars(select(HermesEvent)).all():
        try:
            payload = json.loads(event.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        if payload.get("user_id") == user.id:
            session.delete(event)

    session.execute(delete(Notification).where(Notification.user_id == user.id))
    session.execute(delete(UserAlertPreference).where(UserAlertPreference.user_id == user.id))
    session.execute(delete(UserOutageMatch).where(UserOutageMatch.user_id == user.id))
    session.delete(user)
