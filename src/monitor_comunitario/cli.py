from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import typer
from rich.console import Console

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.session import SessionLocal
from monitor_comunitario.notifications.telegram_provider import TelegramNotificationProvider
from monitor_comunitario.scraper.celesc_emergency import fetch_celesc_emergency_feed
from monitor_comunitario.scraper.celesc_page import (
    fetch_celesc_municipality_pages,
    fetch_celesc_page,
)
from monitor_comunitario.scraper.parser import extract_relevant_outage_section
from monitor_comunitario.services.emergency_monitoring import (
    run_emergency_monitoring_cycle,
)
from monitor_comunitario.services.hermes_processing import process_created_hermes_events
from monitor_comunitario.services.matching import run_matching_cycle
from monitor_comunitario.services.monitoring import run_monitoring_cycle

app = typer.Typer(help="Monitor ComunitÃ¡rio Celesc development CLI.")
console = Console()


def mask_database_url(database_url: str) -> str:
    """Mask credentials in a database URL before printing it."""
    if not database_url:
        return ""

    parsed = urlsplit(database_url)

    if not parsed.scheme or not parsed.netloc:
        return database_url

    if "@" not in parsed.netloc:
        return database_url

    credentials, host = parsed.netloc.rsplit("@", 1)
    username = credentials.split(":", 1)[0]

    masked_netloc = f"{username}:***@{host}" if username else f"***@{host}"

    return urlunsplit(
        (
            parsed.scheme,
            masked_netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


@app.command()
def doctor() -> None:
    """Print basic environment information."""
    settings = get_settings()
    console.print("[bold green]Monitor ComunitÃ¡rio[/bold green]")
    console.print(f"Environment: {settings.app_env}")
    console.print(f"Timezone: {settings.app_timezone}")
    console.print(f"Celesc URL: {settings.celesc_outages_url}")
    console.print(f"Notification provider: {settings.notification_provider}")
    console.print(f"Database URL: {mask_database_url(settings.database_url)}")


@app.command("db-upgrade")
def db_upgrade(
    revision: str = typer.Argument("head", help="Target Alembic revision."),
) -> None:
    """Apply database migrations."""
    from monitor_comunitario.db.migrations import upgrade_database

    upgrade_database(revision)
    console.print(f"[bold green]Database upgraded to {revision}[/bold green]")


@app.command("db-downgrade")
def db_downgrade(
    revision: str = typer.Argument("-1", help="Target Alembic downgrade revision."),
) -> None:
    """Downgrade database migrations."""
    from monitor_comunitario.db.migrations import downgrade_database

    downgrade_database(revision)
    console.print(f"[bold yellow]Database downgraded to {revision}[/bold yellow]")


@app.command("db-stamp")
def db_stamp(
    revision: str = typer.Argument("head", help="Revision to stamp without running migrations."),
) -> None:
    """Mark the database as being at a revision without running migrations."""
    from monitor_comunitario.db.migrations import stamp_database

    stamp_database(revision)
    console.print(f"[bold green]Database stamped as {revision}[/bold green]")


@app.command("db-current")
def db_current() -> None:
    """Print the current database revision."""
    from monitor_comunitario.db.migrations import show_current_revision

    show_current_revision()


@app.command("db-history")
def db_history() -> None:
    """Print database migration history."""
    from monitor_comunitario.db.migrations import show_migration_history

    show_migration_history()


@app.command("db-revision")
def db_revision(
    message: str = typer.Argument(..., help="Migration message."),
    autogenerate: bool = typer.Option(
        False,
        "--autogenerate",
        "-a",
        help="Autogenerate migration from SQLAlchemy metadata.",
    ),
) -> None:
    """Create a new Alembic revision."""
    from monitor_comunitario.db.migrations import create_revision

    create_revision(message=message, autogenerate=autogenerate)


@app.command()
def scrape() -> None:
    """Capture the Celesc scheduled outage page with Playwright."""
    import asyncio

    settings = get_settings()

    result = asyncio.run(
        fetch_celesc_page(
            url=settings.celesc_outages_url,
            snapshot_dir=settings.snapshot_dir,
            headless=settings.scraper_headless,
            timeout_ms=settings.scraper_timeout_ms,
        )
    )

    relevant_text = extract_relevant_outage_section(result.text)
    preview = relevant_text[:1_000] if relevant_text else result.text[:1_000]

    console.print("[bold green]Celesc scrape completed[/bold green]")
    console.print(f"URL: {result.url}")
    console.print(f"Fetched at: {result.fetched_at.isoformat()}")
    console.print(f"HTML snapshot: {result.html_snapshot_path}")
    console.print(f"Text snapshot: {result.text_snapshot_path}")
    console.print(f"HTML bytes: {len(result.html.encode('utf-8'))}")
    console.print(f"Text chars: {len(result.text)}")

    if preview:
        console.print("")
        console.print("[bold]Text preview[/bold]")
        console.print(preview)


@app.command("scrape-municipalities")
def scrape_municipalities(
    limit: int = typer.Option(
        0,
        "--limit",
        help="Maximum number of municipalities to capture. Use 0 for all.",
    ),
) -> None:
    """Select active municipalities and capture one snapshot per option."""
    import asyncio

    settings = get_settings()
    max_options = limit if limit > 0 else None

    result = asyncio.run(
        fetch_celesc_municipality_pages(
            url=settings.celesc_outages_url,
            snapshot_dir=settings.snapshot_dir,
            headless=settings.scraper_headless,
            timeout_ms=settings.scraper_timeout_ms,
            max_options=max_options,
        )
    )

    console.print("[bold green]Celesc municipality scrape completed[/bold green]")
    console.print(f"URL: {result.url}")
    console.print(f"Fetched at: {result.fetched_at.isoformat()}")
    console.print(f"Active options found: {len(result.options)}")
    console.print(f"Municipalities captured: {len(result.captures)}")
    console.print(f"Index: {result.index_path}")

    if result.options:
        console.print("")
        console.print("[bold]Options preview[/bold]")

        for option in result.options[:10]:
            console.print(f"- {option.label} ({option.value})")


@app.command("scrape-emergency")
def scrape_emergency() -> None:
    """Capture current municipal emergency outages from Celesc."""
    import asyncio

    settings = get_settings()
    result = asyncio.run(
        fetch_celesc_emergency_feed(
            url=settings.celesc_emergency_url,
            snapshot_dir=settings.snapshot_dir,
            timeout_ms=settings.scraper_timeout_ms,
        )
    )

    console.print("[bold green]Celesc emergency scrape completed[/bold green]")
    console.print(f"URL: {result.url}")
    console.print(f"Fetched at: {result.fetched_at.isoformat()}")
    console.print(f"Active municipalities: {len(result.outages)}")
    console.print(f"Snapshot: {result.snapshot_path}")

    for outage in result.outages[:10]:
        console.print(
            f"- {outage.municipality}: {outage.affected_units} "
            f"of {outage.total_units} units without energy"
        )


@app.command("run-emergency")
def run_emergency() -> None:
    """Collect and match current emergency outages."""
    result = run_emergency_monitoring_cycle()
    console.print("[bold green]Emergency monitoring completed[/bold green]")
    console.print(f"Active localities: {result.active_localities}")
    console.print(f"New localities: {result.new_localities}")
    console.print(f"Notifications created: {result.matching.notifications_created}")


@app.command()
def run_once(
    limit: int = typer.Option(
        0,
        "--limit",
        help="Maximum number of municipalities to process. Use 0 for all.",
    ),
) -> None:
    """Run one monitoring cycle, persist notices and create notifications."""
    init_db()
    max_options = limit if limit > 0 else None
    result = run_monitoring_cycle(limit=max_options)
    run = result.run

    console.print("[bold green]Monitoring run completed[/bold green]")
    console.print(f"Run ID: {run.id}")
    console.print(f"Status: {run.status}")
    console.print(f"Municipality options found: {run.municipalities_found}")
    console.print(f"Municipalities captured: {run.municipalities_captured}")
    console.print(f"Parsed notices: {run.notices_found}")
    console.print(f"Persisted notices: {run.notices_persisted}")
    console.print(f"New notices: {run.notices_created}")
    console.print(f"Users checked: {run.users_checked}")
    console.print(f"Matches created: {run.matches_created}")
    console.print(f"Notifications created: {run.notifications_created}")
    console.print(f"Index: {run.raw_snapshot_path}")

    if run.error_message:
        console.print(f"[red]Error: {run.error_message}[/red]")


@app.command("match-notices")
def match_notices() -> None:
    """Match existing users against persisted notices and create notifications."""
    init_db()

    with SessionLocal() as session:
        summary = run_matching_cycle(session)

    console.print("[bold green]Matching completed[/bold green]")
    console.print(f"Users checked: {summary.users_checked}")
    console.print(f"Notices checked: {summary.notices_checked}")
    console.print(f"Matches created: {summary.matches_created}")
    console.print(f"Notifications created: {summary.notifications_created}")


@app.command("hermes-process")
def hermes_process(
    limit: int = typer.Option(
        50,
        "--limit",
        help="Maximum number of created Hermes events to process locally.",
    ),
) -> None:
    """Process created Hermes events locally without external delivery."""
    settings = get_settings()
    init_db()
    telegram_provider = (
        TelegramNotificationProvider(
            bot_token=settings.hermes_telegram_bot_token,
            chat_id=settings.hermes_telegram_chat_id,
            api_base_url=settings.hermes_telegram_api_base_url,
        )
        if settings.hermes_telegram_enabled
        else None
    )

    with SessionLocal() as session:
        summary = process_created_hermes_events(
            session,
            limit=limit,
            telegram_enabled=settings.hermes_telegram_enabled,
            telegram_provider=telegram_provider,
        )

    console.print("[bold green]Hermes local processing completed[/bold green]")
    console.print(f"Events checked: {summary.events_checked}")
    console.print(f"Events processed: {summary.events_processed}")
    console.print(f"Events escalated: {summary.events_escalated}")
    console.print(f"Events failed: {summary.events_failed}")

@app.command("telegram-bot")
def telegram_bot() -> None:
    """Run the dedicated Monitor administrative Telegram bot."""
    import asyncio

    from monitor_comunitario.notifications.telegram_bot import run_telegram_bot

    settings = get_settings()
    if not settings.monitor_telegram_enabled:
        raise typer.BadParameter("MONITOR_TELEGRAM_ENABLED must be true.")
    asyncio.run(run_telegram_bot(settings))


@app.command()
def worker() -> None:
    """Start the scheduled monitoring worker."""
    from apscheduler.schedulers.blocking import BlockingScheduler  # type: ignore[import-untyped]
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
    from apscheduler.triggers.interval import IntervalTrigger  # type: ignore[import-untyped]

    settings = get_settings()
    timezone = ZoneInfo(settings.app_timezone)

    scheduler = BlockingScheduler(timezone=timezone)
    trigger = CronTrigger(
        hour=settings.scheduler_hour,
        minute=settings.scheduler_minute,
        timezone=timezone,
    )

    scheduler.add_job(
        lambda: run_monitoring_cycle(limit=None),
        trigger=trigger,
        id="daily-celesc-monitor",
        replace_existing=True,
    )
    scheduler.add_job(
        run_emergency_monitoring_cycle,
        trigger=IntervalTrigger(
            minutes=settings.emergency_scheduler_interval_minutes,
            timezone=timezone,
        ),
        id="celesc-emergency-monitor",
        replace_existing=True,
    )

    console.print("[bold green]Worker started[/bold green]")
    console.print(
        f"Scheduled daily at {settings.scheduler_hour:02d}:"
        f"{settings.scheduler_minute:02d} {settings.app_timezone}"
    )
    console.print(
        "Emergency collection every "
        f"{settings.emergency_scheduler_interval_minutes} minutes"
    )

    scheduler.start()


@app.command()
def snapshots() -> None:
    """List saved scraper snapshots."""
    settings = get_settings()
    snapshot_dir = Path(settings.snapshot_dir)

    if not snapshot_dir.exists():
        console.print("[yellow]No snapshot directory found.[/yellow]")
        return

    for file in sorted(snapshot_dir.iterdir(), reverse=True):
        if file.is_file():
            console.print(str(file))


if __name__ == "__main__":
    app()
