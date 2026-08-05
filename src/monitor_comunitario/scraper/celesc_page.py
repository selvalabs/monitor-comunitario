import json
import re
import unicodedata
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from playwright.async_api import (
    Error as PlaywrightError,
)
from playwright.async_api import (
    Frame,
    Locator,
    Page,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from monitor_comunitario.scraper.parser import clean_page_text


@dataclass(frozen=True)
class CelescScrapeResult:
    """Result produced by a Celesc outage page capture."""

    url: str
    fetched_at: datetime
    html: str
    text: str
    html_snapshot_path: Path
    text_snapshot_path: Path


@dataclass(frozen=True)
class MunicipalityOption:
    """One active option from Celesc's municipality selector."""

    label: str
    value: str


@dataclass(frozen=True)
class MunicipalityCapture:
    """HTML/text captured after selecting one municipality."""

    option: MunicipalityOption
    html: str
    text: str
    html_snapshot_path: Path
    text_snapshot_path: Path


@dataclass(frozen=True)
class CelescMunicipalityScrapeResult:
    """Result produced by selecting all available municipalities."""

    url: str
    fetched_at: datetime
    options: list[MunicipalityOption]
    captures: list[MunicipalityCapture]
    index_path: Path


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def build_snapshot_stem(fetched_at: datetime) -> str:
    """Build a filesystem-safe snapshot name."""
    return f"celesc-outages-{fetched_at.strftime('%Y%m%dT%H%M%SZ')}"


def build_safe_snapshot_slug(value: str) -> str:
    """Build a lowercase ASCII slug for snapshot filenames."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "municipio"


def is_placeholder_municipality_option(option: MunicipalityOption) -> bool:
    """Return whether a municipality option is only a placeholder."""
    label = option.label.strip().casefold()
    value = option.value.strip().casefold()

    placeholders = (
        "",
        "0",
        "-1",
        "selecione",
        "selecione...",
        "selecione o município",
        "selecione o municipio",
        "município",
        "municipio",
    )

    return label in placeholders or value in placeholders


async def accept_cookie_banner(page: Page) -> None:
    """Try to accept Celesc's cookie banner without failing the scrape."""
    candidates = [
        page.get_by_role("button", name="Estou ciente"),
        page.get_by_text("Estou ciente", exact=True),
    ]

    for candidate in candidates:
        try:
            if await candidate.count() > 0:
                await candidate.first.click(timeout=2_000)
                return
        except PlaywrightTimeoutError:
            continue


async def get_select_options(select: Locator) -> list[MunicipalityOption]:
    """Extract active options from a native HTML select element."""
    raw_options = cast(
        list[dict[str, Any]],
        await select.locator("option").evaluate_all(
            """options => options.map(option => ({
                label: (option.textContent || '').trim(),
                value: (option.value || '').trim(),
                disabled: option.disabled
            }))"""
        ),
    )

    options: list[MunicipalityOption] = []

    for raw_option in raw_options:
        if bool(raw_option.get("disabled")):
            continue

        option = MunicipalityOption(
            label=str(raw_option.get("label", "")).strip(),
            value=str(raw_option.get("value", "")).strip(),
        )

        if is_placeholder_municipality_option(option):
            continue

        options.append(option)

    return options


async def find_municipality_select_in_frames(page: Page) -> tuple[Frame, Locator] | None:
    """Find the native select that contains municipality options in any frame.

    The Celesc page embeds the interruption search UI inside an iframe. The
    main DOM has no select, so we must inspect every Playwright frame.
    """
    best_result: tuple[Frame, Locator] | None = None
    best_option_count = 0

    for frame in page.frames:
        try:
            selects = frame.locator("select")
            select_count = await selects.count()
        except PlaywrightError:
            continue

        for index in range(select_count):
            candidate = selects.nth(index)
            options = await get_select_options(candidate)

            if len(options) > best_option_count:
                best_result = (frame, candidate)
                best_option_count = len(options)

    return best_result


async def click_ok_button(frame: Frame) -> None:
    """Click the OK button associated with the municipality selector."""
    candidates = [
        frame.get_by_role("button", name=re.compile(r"^ok$", re.IGNORECASE)),
        frame.locator("input[type='submit'][value='OK']"),
        frame.locator("input[type='button'][value='OK']"),
        frame.locator("button:has-text('OK')"),
    ]

    for candidate in candidates:
        try:
            if await candidate.count() > 0:
                await candidate.first.click(timeout=3_000)
                return
        except PlaywrightTimeoutError:
            continue


async def capture_frame_text_and_html(frame: Frame, timeout_ms: int) -> tuple[str, str]:
    """Capture current frame HTML and cleaned visible text."""
    html = await frame.content()
    raw_text = await frame.locator("body").inner_text(timeout=timeout_ms)
    return html, clean_page_text(raw_text)


async def fetch_celesc_page(
    url: str,
    snapshot_dir: str,
    headless: bool = True,
    timeout_ms: int = 30_000,
) -> CelescScrapeResult:
    """Fetch the Celesc outage page and persist HTML/TXT snapshots."""
    fetched_at = utc_now()
    snapshot_path = Path(snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)

    stem = build_snapshot_stem(fetched_at)

    html_snapshot_path = snapshot_path / f"{stem}.html"
    text_snapshot_path = snapshot_path / f"{stem}.txt"

    latest_html_path = snapshot_path / "latest-celesc-outages.html"
    latest_text_path = snapshot_path / "latest-celesc-outages.txt"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        page.set_default_timeout(timeout_ms)

        await page.goto(url, wait_until="networkidle")
        await accept_cookie_banner(page)
        await page.wait_for_load_state("networkidle")

        html = await page.content()
        raw_text = await page.locator("body").inner_text(timeout=timeout_ms)
        text = clean_page_text(raw_text)

        await browser.close()

    html_snapshot_path.write_text(html, encoding="utf-8")
    text_snapshot_path.write_text(text, encoding="utf-8")

    latest_html_path.write_text(html, encoding="utf-8")
    latest_text_path.write_text(text, encoding="utf-8")

    return CelescScrapeResult(
        url=url,
        fetched_at=fetched_at,
        html=html,
        text=text,
        html_snapshot_path=html_snapshot_path,
        text_snapshot_path=text_snapshot_path,
    )


async def fetch_celesc_municipality_pages(
    url: str,
    snapshot_dir: str,
    headless: bool = True,
    timeout_ms: int = 30_000,
    max_options: int | None = None,
) -> CelescMunicipalityScrapeResult:
    """Select each active municipality and persist per-municipality snapshots."""
    fetched_at = utc_now()
    snapshot_path = Path(snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)

    stem = build_snapshot_stem(fetched_at)
    index_path = snapshot_path / f"{stem}-municipalities.json"
    latest_index_path = snapshot_path / "latest-celesc-municipalities.json"

    captures: list[MunicipalityCapture] = []
    options: list[MunicipalityOption] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        page.set_default_timeout(timeout_ms)

        await page.goto(url, wait_until="networkidle")
        await accept_cookie_banner(page)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1_000)

        select_result = await find_municipality_select_in_frames(page)

        if select_result is not None:
            frame, select = select_result
            options = await get_select_options(select)
            limited_options = options[:max_options] if max_options else options

            for option in limited_options:
                refreshed_result = await find_municipality_select_in_frames(page)

                if refreshed_result is None:
                    break

                frame, select = refreshed_result

                await select.select_option(value=option.value)
                await click_ok_button(frame)
                await page.wait_for_timeout(1_500)

                with suppress(PlaywrightTimeoutError):
                    await page.wait_for_load_state("networkidle", timeout=5_000)

                refreshed_result = await find_municipality_select_in_frames(page)

                if refreshed_result is not None:
                    frame, _ = refreshed_result

                html, text = await capture_frame_text_and_html(frame, timeout_ms)
                option_slug = build_safe_snapshot_slug(option.label)

                html_snapshot_path = snapshot_path / f"{stem}-{option_slug}.html"
                text_snapshot_path = snapshot_path / f"{stem}-{option_slug}.txt"

                html_snapshot_path.write_text(html, encoding="utf-8")
                text_snapshot_path.write_text(text, encoding="utf-8")

                captures.append(
                    MunicipalityCapture(
                        option=option,
                        html=html,
                        text=text,
                        html_snapshot_path=html_snapshot_path,
                        text_snapshot_path=text_snapshot_path,
                    )
                )

        await browser.close()

    index_payload = {
        "url": url,
        "fetched_at": fetched_at.isoformat(),
        "options": [{"label": option.label, "value": option.value} for option in options],
        "captures": [
            {
                "municipality": capture.option.label,
                "value": capture.option.value,
                "html_snapshot_path": str(capture.html_snapshot_path),
                "text_snapshot_path": str(capture.text_snapshot_path),
                "text_chars": len(capture.text),
                "html_bytes": len(capture.html.encode("utf-8")),
                "text_preview": capture.text[:1000],
            }
            for capture in captures
        ],
    }

    index_json = json.dumps(index_payload, ensure_ascii=False, indent=2)
    index_path.write_text(index_json, encoding="utf-8")
    latest_index_path.write_text(index_json, encoding="utf-8")

    return CelescMunicipalityScrapeResult(
        url=url,
        fetched_at=fetched_at,
        options=options,
        captures=captures,
        index_path=index_path,
    )


async def fetch_celesc_page_html(
    url: str,
    snapshot_dir: str,
    headless: bool = True,
    timeout_ms: int = 30_000,
) -> str:
    """Backward-compatible helper that returns only HTML."""
    result = await fetch_celesc_page(
        url=url,
        snapshot_dir=snapshot_dir,
        headless=headless,
        timeout_ms=timeout_ms,
    )
    return result.html

