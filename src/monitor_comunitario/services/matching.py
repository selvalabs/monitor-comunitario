from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import Notification, OutageNotice, User, UserOutageMatch
from monitor_comunitario.matcher.normalizer import (
    normalize_municipality,
    normalize_neighborhood,
    normalize_street_name,
    normalize_text,
)
from monitor_comunitario.matcher.scoring import MatchLevel, MatchResult, score_text


@dataclass(frozen=True)
class MatchingSummary:
    """Summary of one matching cycle."""

    users_checked: int
    notices_checked: int
    matches_created: int
    notifications_created: int


def _notice_search_text(notice: OutageNotice) -> str:
    """Build a searchable text field from all notice location fields."""
    return normalize_text(
        " ".join(
            [
                notice.municipality,
                notice.neighborhood,
                notice.street,
                notice.description,
                notice.raw_text,
            ]
        )
    )


def _exact_or_fuzzy_municipality_match(user: User, notice: OutageNotice) -> bool:
    user_municipality = normalize_municipality(user.municipality)
    notice_municipality = normalize_municipality(notice.municipality)

    if not user_municipality or not notice_municipality:
        return False

    if user_municipality == notice_municipality:
        return True

    return score_text(user_municipality, notice_municipality) >= 92


def match_user_to_notice(user: User, notice: OutageNotice) -> MatchResult:
    """Compare one user address against one outage notice."""
    if user.is_active is False:
        return MatchResult(MatchLevel.NONE, 0.0, "User is inactive.")

    if user.notifications_approved is False:
        return MatchResult(MatchLevel.NONE, 0.0, "User is not approved for notifications.")

    if not _exact_or_fuzzy_municipality_match(user, notice):
        return MatchResult(MatchLevel.NONE, 0.0, "Municipality does not match.")

    notice_text = _notice_search_text(notice)

    user_street = normalize_street_name(user.street)

    if user_street:
        street_score = score_text(user_street, notice_text)

        if user_street in notice_text or street_score >= 88:
            return MatchResult(
                MatchLevel.STREET,
                street_score,
                "User street appears to match the outage notice.",
            )

    user_neighborhood = normalize_neighborhood(user.neighborhood)

    if user_neighborhood:
        neighborhood_score = score_text(user_neighborhood, notice_text)

        if user_neighborhood in notice_text or neighborhood_score >= 88:
            return MatchResult(
                MatchLevel.NEIGHBORHOOD,
                neighborhood_score,
                "User neighborhood appears to match the outage notice.",
            )

    combined_user_address = normalize_text(
        " ".join([user.neighborhood, user.street, user.number, user.zipcode])
    )

    if combined_user_address:
        fuzzy_score = score_text(combined_user_address, notice_text)

        if fuzzy_score >= 82:
            return MatchResult(
                MatchLevel.FUZZY,
                fuzzy_score,
                "User address is textually similar to the outage notice.",
            )

    if user.accept_municipality_wide_alerts:
        return MatchResult(
            MatchLevel.UNCERTAIN,
            60.0,
            "Municipality matches, but neighborhood/street detail is insufficient.",
        )

    return MatchResult(
        MatchLevel.MUNICIPALITY,
        50.0,
        "Municipality matches, but user disabled broad municipality alerts.",
    )


def get_existing_match(
    session: Session,
    user_id: int,
    outage_notice_id: int,
) -> UserOutageMatch | None:
    """Return an existing match between a user and notice."""
    statement = select(UserOutageMatch).where(
        UserOutageMatch.user_id == user_id,
        UserOutageMatch.outage_notice_id == outage_notice_id,
    )
    return session.scalar(statement)


def persist_match(
    session: Session,
    user: User,
    notice: OutageNotice,
    result: MatchResult,
) -> tuple[UserOutageMatch, bool]:
    """Persist one positive match, deduplicating by user/notice."""
    existing = get_existing_match(session, user.id, notice.id)

    if existing is not None:
        return existing, False

    match = UserOutageMatch(
        user_id=user.id,
        outage_notice_id=notice.id,
        match_level=result.level.value,
        match_score=result.score,
        match_reason=result.reason,
    )

    session.add(match)
    session.commit()
    session.refresh(match)

    return match, True


def build_notification_message(
    user: User,
    notice: OutageNotice,
    result: MatchResult,
) -> tuple[str, str]:
    """Build an in-app notification title and message."""
    title = f"Possível desligamento em {notice.municipality}"

    area_parts = [part for part in [notice.neighborhood, notice.street] if part]
    area = " / ".join(area_parts) if area_parts else "área informada pela Celesc"

    message = (
        f"Encontramos um desligamento programado que pode afetar o endereço cadastrado "
        f"para {user.name}.\n\n"
        f"Município: {notice.municipality}\n"
        f"Área: {area}\n"
        f"Confiança: {result.level.value} ({result.score:.0f})\n\n"
        f"Descrição:\n{notice.description or notice.raw_text}\n\n"
        "Este alerta usa informações públicas da Celesc e não é um canal oficial. "
        "A programação pode sofrer alteração ou cancelamento."
    )

    return title, message


def get_existing_notification(
    session: Session,
    user_id: int,
    outage_notice_id: int,
    channel: str = "app",
) -> Notification | None:
    """Return an existing notification for a user/notice/channel."""
    statement = select(Notification).where(
        Notification.user_id == user_id,
        Notification.outage_notice_id == outage_notice_id,
        Notification.channel == channel,
    )
    return session.scalar(statement)


def create_app_notification(
    session: Session,
    user: User,
    notice: OutageNotice,
    result: MatchResult,
) -> tuple[Notification, bool]:
    """Create an in-app notification, deduplicating by user/notice/channel."""
    existing = get_existing_notification(session, user.id, notice.id, channel="app")

    if existing is not None:
        return existing, False

    title, message = build_notification_message(user, notice, result)

    notification = Notification(
        user_id=user.id,
        outage_notice_id=notice.id,
        channel="app",
        status="created",
        title=title,
        message=message,
    )

    session.add(notification)
    session.commit()
    session.refresh(notification)

    return notification, True


def run_matching_cycle(session: Session) -> MatchingSummary:
    """Match all active, notification-approved users against persisted notices."""
    users = list(
        session.scalars(
            select(User).where(
                User.is_active.is_(True),
                User.notifications_approved.is_(True),
            )
        ).all()
    )
    notices = list(session.scalars(select(OutageNotice)).all())

    matches_created = 0
    notifications_created = 0

    for user in users:
        for notice in notices:
            result = match_user_to_notice(user, notice)

            if result.level == MatchLevel.NONE:
                continue

            if result.level == MatchLevel.MUNICIPALITY and not user.accept_municipality_wide_alerts:
                continue

            _, match_created = persist_match(session, user, notice, result)

            if match_created:
                matches_created += 1

            _, notification_created = create_app_notification(session, user, notice, result)

            if notification_created:
                notifications_created += 1

    return MatchingSummary(
        users_checked=len(users),
        notices_checked=len(notices),
        matches_created=matches_created,
        notifications_created=notifications_created,
    )
