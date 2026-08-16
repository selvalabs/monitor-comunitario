import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from typing import Any

import httpx

EMERGENCY_FEED_URL = "https://celgeoweb.celesc.com.br/json/tabelas.js"
_ASSIGNMENT_PATTERN = re.compile(
    r"^\s*var\s+(?:mapaIndicador|visaoGeralPublico)\s*=\s*"
    r"(?P<payload>\{.*\})\s*;?\s*$",
    re.DOTALL,
)
_MUNICIPALITY_PATTERN = re.compile(r"<th[^>]*>\s*(?P<value>[^<]+?)\s*</th>", re.IGNORECASE)
_TOTAL_UNITS_PATTERN = re.compile(
    r"Total de unidades consumidoras\s+(?P<value>[\d.]+)",
    re.IGNORECASE,
)
_AFFECTED_UNITS_PATTERN = re.compile(
    r"Sem energia\s+(?P<value>[\d.]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EmergencyOutage:
    """Current municipal emergency outage reported by Celesc."""

    municipality: str
    municipality_id: int
    neighborhood: str
    neighborhood_id: int
    affected_units: int
    total_units: int
    raw_text: str


@dataclass(frozen=True)
class EmergencyScrapeResult:
    """Result produced by the public emergency feed."""

    url: str
    fetched_at: datetime
    outages: list[EmergencyOutage]
    snapshot_path: Path


def _parse_count(value: str) -> int:
    return int(value.replace(".", "").replace(",", "").strip())


def _visible_text(raw_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _extract_payload(text: str) -> dict[str, Any]:
    match = _ASSIGNMENT_PATTERN.match(text)
    if match is None:
        raise ValueError("Celesc emergency feed assignment not found")

    payload = re.sub(r"\[\s*,", "[", match.group("payload"))

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("mapaIndicador payload is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Celesc emergency feed payload must be an object")

    return parsed


def parse_emergency_details_feed(text: str) -> list[EmergencyOutage]:
    """Parse active accidental outages grouped by municipality and neighborhood."""
    payload = _extract_payload(text)
    regionals = payload.get("REGIONAIS")
    if not isinstance(regionals, list):
        raise ValueError("visaoGeralPublico payload must contain REGIONAIS")

    outages: list[EmergencyOutage] = []
    for regional in regionals:
        if not isinstance(regional, dict):
            raise ValueError("REGIONAIS entries must be objects")

        cities = regional.get("CIDADES", [])
        if not isinstance(cities, list):
            raise ValueError("CIDADES entries must be a list")

        for city in cities:
            if not isinstance(city, dict):
                raise ValueError("CIDADES entries must be objects")

            neighborhoods = city.get("BAIRROS", [])
            if not isinstance(neighborhoods, list):
                raise ValueError("BAIRROS entries must be a list")

            for neighborhood in neighborhoods:
                if not isinstance(neighborhood, dict):
                    raise ValueError("BAIRROS entries must be objects")

                affected_units = _parse_count(str(neighborhood["QUANTIDADE_ACIDENTAL"]))
                if affected_units <= 0:
                    continue

                municipality = str(city["CIDADE"]).strip()
                locality = str(neighborhood["BAIRRO"]).strip()
                raw_text = f"{municipality} / {locality}"
                outages.append(
                    EmergencyOutage(
                        municipality=municipality,
                        municipality_id=int(city["ID_CIDADE"]),
                        neighborhood=locality,
                        neighborhood_id=int(neighborhood["ID_BAIRRO"]),
                        affected_units=affected_units,
                        total_units=_parse_count(str(neighborhood["QUANTIDADE_TOTAL"])),
                        raw_text=raw_text,
                    )
                )

    return outages


def parse_emergency_feed(text: str) -> list[EmergencyOutage]:
    """Parse active municipal outages without executing feed JavaScript."""
    payload = _extract_payload(text)
    if not isinstance(payload.get("municipios"), list):
        raise ValueError("mapaIndicador payload must contain municipios")
    outages: list[EmergencyOutage] = []

    for item in payload["municipios"]:
        if not isinstance(item, dict):
            raise ValueError("municipios entries must be objects")

        try:
            municipality_id = int(item["nr_municipio"])
            raw_text = str(item["ds_informacao"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("municipios entry is missing required fields") from exc

        municipality_match = _MUNICIPALITY_PATTERN.search(raw_text)
        visible_text = _visible_text(raw_text)
        total_match = _TOTAL_UNITS_PATTERN.search(visible_text)
        affected_match = _AFFECTED_UNITS_PATTERN.search(visible_text)

        if not municipality_match or not total_match or not affected_match:
            raise ValueError("municipios entry has an unexpected information format")

        affected_units = _parse_count(affected_match.group("value"))
        if affected_units <= 0:
            continue

        outages.append(
            EmergencyOutage(
            municipality=municipality_match.group("value").strip(),
            municipality_id=municipality_id,
            neighborhood="",
            neighborhood_id=0,
            affected_units=affected_units,
                total_units=_parse_count(total_match.group("value")),
                raw_text=raw_text,
            )
        )

    return outages


async def fetch_celesc_emergency_feed(
    snapshot_dir: str,
    url: str = EMERGENCY_FEED_URL,
    timeout_ms: int = 30_000,
) -> EmergencyScrapeResult:
    """Fetch and snapshot the public municipal emergency feed."""
    fetched_at = datetime.now(UTC)
    async with httpx.AsyncClient(timeout=timeout_ms / 1000, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()

    outages = parse_emergency_feed(response.text)
    snapshot_path = Path(snapshot_dir)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    target = snapshot_path / "latest-celesc-emergency-details.js"
    target.write_text(response.text, encoding="utf-8")

    return EmergencyScrapeResult(
        url=url,
        fetched_at=fetched_at,
        outages=outages,
        snapshot_path=target,
    )
