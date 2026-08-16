import asyncio
from dataclasses import dataclass

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.session import SessionLocal
from monitor_comunitario.scraper.casan_alerts import fetch_casan_alerts
from monitor_comunitario.services.matching import MatchingSummary, run_matching_cycle
from monitor_comunitario.services.outage_notices import persist_casan_alerts


@dataclass(frozen=True)
class CasanMonitoringResult:
    """Summary of one public CASAN alert collection."""

    alerts_found: int
    new_alerts: int
    matching: MatchingSummary


def run_casan_monitoring_cycle() -> CasanMonitoringResult:
    """Collect public CASAN alerts and match active alerts to residents."""
    settings = get_settings()
    scrape_result = asyncio.run(
        fetch_casan_alerts(
            url=settings.casan_alerts_url,
            snapshot_dir=settings.snapshot_dir,
            timeout_ms=settings.scraper_timeout_ms,
        )
    )

    with SessionLocal() as session:
        _, new_alerts = persist_casan_alerts(
            session=session,
            alerts=scrape_result.alerts,
            source_url=scrape_result.url,
            observed_at=scrape_result.fetched_at,
        )
        matching = run_matching_cycle(session)

    return CasanMonitoringResult(
        alerts_found=len(scrape_result.alerts),
        new_alerts=new_alerts,
        matching=matching,
    )
