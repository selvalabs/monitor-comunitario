import asyncio
import traceback
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import MonitoringRun, MonitoringRunStatus, utc_now
from monitor_comunitario.db.session import SessionLocal
from monitor_comunitario.scraper.celesc_page import fetch_celesc_municipality_pages
from monitor_comunitario.scraper.parser import parse_outage_notices_from_text
from monitor_comunitario.services.hermes_events import create_hermes_event
from monitor_comunitario.services.matching import run_matching_cycle
from monitor_comunitario.services.outage_notices import persist_parsed_notices


@dataclass(frozen=True)
class MonitoringCycleResult:
    """Result returned by one full monitoring cycle."""

    run: MonitoringRun


def create_monitoring_run(session: Session) -> MonitoringRun:
    """Create a running monitoring record."""
    run = MonitoringRun(status=MonitoringRunStatus.RUNNING.value)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def mark_run_failed(session: Session, run: MonitoringRun, error: BaseException) -> MonitoringRun:
    """Persist a failed monitoring run status."""
    run.status = MonitoringRunStatus.FAILED.value
    run.finished_at = utc_now()
    run.error_message = "".join(
        traceback.format_exception_only(type(error), error)
    ).strip()
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def run_monitoring_cycle(limit: int | None = None) -> MonitoringCycleResult:
    """Run scraper, parser, persistence, matching and notification creation."""
    settings = get_settings()

    with SessionLocal() as session:
        run = create_monitoring_run(session)

        try:
            scrape_result = asyncio.run(
                fetch_celesc_municipality_pages(
                    url=settings.celesc_outages_url,
                    snapshot_dir=settings.snapshot_dir,
                    headless=settings.scraper_headless,
                    timeout_ms=settings.scraper_timeout_ms,
                    max_options=limit,
                )
            )

            parsed_notices = []

            for capture in scrape_result.captures:
                parsed_notices.extend(
                    parse_outage_notices_from_text(
                        capture.text,
                        fallback_municipality=capture.option.label,
                    )
                )

            persisted_notices, created_count = persist_parsed_notices(
                session=session,
                parsed_notices=parsed_notices,
                source_url=scrape_result.url,
            )

            matching_summary = run_matching_cycle(session)

            run.status = MonitoringRunStatus.SUCCESS.value
            run.finished_at = utc_now()
            run.municipalities_found = len(scrape_result.options)
            run.municipalities_captured = len(scrape_result.captures)
            run.notices_found = len(parsed_notices)
            run.notices_persisted = len(persisted_notices)
            run.notices_created = created_count
            run.users_checked = matching_summary.users_checked
            run.matches_created = matching_summary.matches_created
            run.notifications_created = matching_summary.notifications_created
            run.raw_snapshot_path = str(Path(scrape_result.index_path))

            session.add(run)
            session.commit()
            session.refresh(run)

            return MonitoringCycleResult(run=run)

        except Exception as exc:
            failed_run = mark_run_failed(session, run, exc)
            create_hermes_event(
                session=session,
                event_type="worker_failed",
                channel="admin",
                recipient_phone="",
                intent="UNKNOWN_ESCALATE",
                template_key="human_escalation_v1",
                payload={
                    "monitoring_run_id": failed_run.id,
                    "error": str(exc),
                },
            )
            return MonitoringCycleResult(run=failed_run)
