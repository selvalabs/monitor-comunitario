import asyncio
from dataclasses import dataclass

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.session import SessionLocal
from monitor_comunitario.scraper.celesc_emergency import fetch_celesc_emergency_feed
from monitor_comunitario.services.matching import MatchingSummary, run_matching_cycle
from monitor_comunitario.services.outage_notices import persist_emergency_outages


@dataclass(frozen=True)
class EmergencyMonitoringResult:
    """Summary of one emergency feed collection."""

    active_localities: int
    new_localities: int
    matching: MatchingSummary


def run_emergency_monitoring_cycle() -> EmergencyMonitoringResult:
    """Collect current emergency outages and match them to approved residents."""
    settings = get_settings()
    scrape_result = asyncio.run(
        fetch_celesc_emergency_feed(
            url=settings.celesc_emergency_url,
            snapshot_dir=settings.snapshot_dir,
            timeout_ms=settings.scraper_timeout_ms,
        )
    )

    with SessionLocal() as session:
        _, new_localities = persist_emergency_outages(
            session=session,
            outages=scrape_result.outages,
            source_url=scrape_result.url,
            observed_at=scrape_result.fetched_at,
        )
        matching = run_matching_cycle(session)

    return EmergencyMonitoringResult(
        active_localities=len(scrape_result.outages),
        new_localities=new_localities,
        matching=matching,
    )
