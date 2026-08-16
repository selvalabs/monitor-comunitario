import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx

CASAN_ALERTS_URL = "https://e.casan.com.br/avisos/"
_NORMALIZATION_PATTERNS = (
    r"abastecimento\s+(?:foi\s+)?normaliz",
    r"fornecimento\s+(?:foi\s+)?normaliz",
    r"conserto\s+(?:foi\s+)?conclu",
    r"sistema\s+(?:foi\s+)?aberto",
    r"servi[cç]o\s+(?:foi\s+)?normaliz",
)


@dataclass(frozen=True)
class CasanWaterAlert:
    """Public CASAN water-supply communication."""

    notified_at: str
    municipality: str
    neighborhood: str
    street: str
    occurrence: str
    raw_text: str
    normalization_confirmed: bool


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(_normalize_text("".join(self._cell)))
            self._cell = None
        elif normalized_tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _extract_segment(text: str, labels: tuple[str, ...], next_labels: tuple[str, ...]) -> str:
    label_pattern = "|".join(labels)
    next_pattern = "|".join(next_labels)
    match = re.search(
        rf"(?:{label_pattern})\s*:\s*(.*?)(?=\s+(?:{next_pattern})\s*:|$)",
        text,
        flags=re.IGNORECASE,
    )
    return _normalize_text(match.group(1)) if match else ""


def _has_normalization_confirmation(text: str) -> bool:
    normalized = text.casefold()
    return any(re.search(pattern, normalized) for pattern in _NORMALIZATION_PATTERNS)


def parse_casan_alerts_html(html: str) -> list[CasanWaterAlert]:
    """Parse public CASAN alert table rows without executing page scripts."""
    parser = _TableParser()
    parser.feed(html)
    alerts: list[CasanWaterAlert] = []

    for row in parser.rows:
        if len(row) < 2:
            continue

        notified_at, raw_text = row[0], row[1]
        municipality = _extract_segment(
            raw_text,
            (r"Município(?:\(s\))?", r"Municipio(?:\(s\))?"),
            (
                r"Bairro(?:\(s\))?",
                r"Rua(?:\(s\))?",
                r"Ocorrência",
                r"Ocorrencia",
            ),
        )
        neighborhood = _extract_segment(
            raw_text,
            (r"Bairro(?:\(s\))?",),
            (r"Rua(?:\(s\))?", r"Ocorrência", r"Ocorrencia"),
        )
        street = _extract_segment(
            raw_text,
            (r"Rua(?:\(s\))?",),
            (r"Ocorrência", r"Ocorrencia"),
        )
        occurrence = _extract_segment(
            raw_text,
            (r"Ocorrência", r"Ocorrencia"),
            (),
        )

        if not municipality or not occurrence:
            continue

        alerts.append(
            CasanWaterAlert(
                notified_at=notified_at,
                municipality=municipality,
                neighborhood=neighborhood,
                street=street,
                occurrence=occurrence,
                raw_text=raw_text,
                normalization_confirmed=_has_normalization_confirmation(occurrence),
            )
        )

    return alerts


@dataclass(frozen=True)
class CasanScrapeResult:
    url: str
    fetched_at: datetime
    alerts: list[CasanWaterAlert]
    snapshot_path: Path


async def fetch_casan_alerts(
    snapshot_dir: str,
    url: str = CASAN_ALERTS_URL,
    timeout_ms: int = 30_000,
) -> CasanScrapeResult:
    """Fetch and snapshot the public CASAN water alerts page."""
    fetched_at = datetime.now(UTC)
    async with httpx.AsyncClient(timeout=timeout_ms / 1000, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    alerts = parse_casan_alerts_html(response.text)
    snapshot_path = Path(snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    target = snapshot_path / "latest-casan-water-alerts.html"
    target.write_text(response.text, encoding="utf-8")

    return CasanScrapeResult(
        url=url,
        fetched_at=fetched_at,
        alerts=alerts,
        snapshot_path=target,
    )
