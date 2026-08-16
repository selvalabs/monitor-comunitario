from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import OutageNotice
from monitor_comunitario.scraper.celesc_emergency import EmergencyOutage
from monitor_comunitario.scraper.parser import ParsedOutageNotice


def build_notice_content_hash(notice: ParsedOutageNotice, source_url: str) -> str:
    """Build a stable hash to deduplicate outage notices."""
    hash_input = "|".join(
        [
            source_url.strip(),
            notice.municipality.strip().casefold(),
            notice.neighborhood.strip().casefold(),
            notice.street.strip().casefold(),
            notice.description.strip().casefold(),
            notice.raw_text.strip().casefold(),
        ]
    )

    return sha256(hash_input.encode("utf-8")).hexdigest()


def get_notice_by_hash(session: Session, content_hash: str) -> OutageNotice | None:
    """Return an existing notice by hash, if present."""
    statement = select(OutageNotice).where(OutageNotice.content_hash == content_hash)
    return session.scalar(statement)


def persist_parsed_notice(
    session: Session,
    parsed_notice: ParsedOutageNotice,
    source_url: str,
) -> tuple[OutageNotice, bool]:
    """Persist one parsed notice.

    Returns `(notice, created)`.
    """
    content_hash = build_notice_content_hash(parsed_notice, source_url)
    existing = get_notice_by_hash(session, content_hash)

    if existing is not None:
        return existing, False

    notice = OutageNotice(
        source="celesc",
        source_url=source_url,
        municipality=parsed_notice.municipality,
        neighborhood=parsed_notice.neighborhood,
        street=parsed_notice.street,
        description=parsed_notice.description,
        raw_text=parsed_notice.raw_text,
        content_hash=content_hash,
    )

    session.add(notice)
    session.commit()
    session.refresh(notice)

    return notice, True


def persist_parsed_notices(
    session: Session,
    parsed_notices: list[ParsedOutageNotice],
    source_url: str,
) -> tuple[list[OutageNotice], int]:
    """Persist parsed notices and return all records plus created count."""
    notices: list[OutageNotice] = []
    created_count = 0

    for parsed_notice in parsed_notices:
        notice, created = persist_parsed_notice(
            session=session,
            parsed_notice=parsed_notice,
            source_url=source_url,
        )
        notices.append(notice)

        if created:
            created_count += 1

    return notices, created_count


def persist_emergency_outages(
    session: Session,
    outages: list[EmergencyOutage],
    source_url: str,
    observed_at: datetime | None = None,
) -> tuple[list[OutageNotice], int]:
    """Upsert current emergency outages and resolve missing localities."""
    seen_at = observed_at or datetime.now(UTC)
    source_keys = {
        f"celesc-emergency:{outage.municipality_id}:{outage.neighborhood_id}"
        for outage in outages
    }
    existing = {
        notice.source_key: notice
        for notice in session.scalars(
            select(OutageNotice).where(OutageNotice.notice_type == "emergency")
        ).all()
        if notice.source_key
    }

    persisted: list[OutageNotice] = []
    created_count = 0

    for outage in outages:
        source_key = f"celesc-emergency:{outage.municipality_id}:{outage.neighborhood_id}"
        notice = existing.get(source_key)
        description = (
            f"Ocorrência emergencial: {outage.affected_units} unidades "
            f"sem energia na localidade informada pela Celesc."
        )

        if notice is None:
            notice = OutageNotice(
                source="celesc-emergency",
                notice_type="emergency",
                source_url=source_url,
                source_key=source_key,
                municipality=outage.municipality,
                neighborhood=outage.neighborhood,
                description=description,
                raw_text=outage.raw_text,
                content_hash=sha256(source_key.encode("utf-8")).hexdigest(),
                is_active=True,
                last_seen_at=seen_at,
            )
            session.add(notice)
            created_count += 1
        else:
            notice.source_url = source_url
            notice.municipality = outage.municipality
            notice.neighborhood = outage.neighborhood
            notice.description = description
            notice.raw_text = outage.raw_text
            notice.is_active = True
            notice.last_seen_at = seen_at
            notice.resolved_at = None

        persisted.append(notice)

    for source_key, notice in existing.items():
        if source_key not in source_keys and notice.is_active:
            notice.is_active = False
            notice.resolved_at = seen_at

    session.commit()
    for notice in persisted:
        session.refresh(notice)

    return persisted, created_count
