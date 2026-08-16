import pytest

from monitor_comunitario.scraper.celesc_emergency import (
    EmergencyOutage,
    parse_emergency_feed,
)

FEED = (
    'var mapaIndicador = {"municipios":[,'
    '{"nr_municipio":13103,"nr_cor":1,'
    '"ds_informacao":"<th> Laguna </th><td>Total de unidades consumidoras</td>'
    '<td>30.230</td><td>Sem energia</td><td>278</td>"},'
    '{"nr_municipio":13131,"nr_cor":1,'
    '"ds_informacao":"<th> Sangao </th><td>Total de unidades consumidoras</td>'
    '<td>4.850</td><td>Sem energia</td><td>0</td>"}]};'
)


def test_parse_emergency_feed_extracts_only_active_municipalities() -> None:
    result = parse_emergency_feed(FEED)

    assert result == [
        EmergencyOutage(
            municipality="Laguna",
            municipality_id=13103,
            affected_units=278,
            total_units=30230,
            raw_text=(
                "<th> Laguna </th><td>Total de unidades consumidoras</td>"
                "<td>30.230</td><td>Sem energia</td><td>278</td>"
            ),
        )
    ]


def test_parse_emergency_feed_rejects_unexpected_javascript() -> None:
    with pytest.raises(ValueError, match="mapaIndicador"):
        parse_emergency_feed("alert('not data');")


def test_parse_emergency_feed_rejects_missing_fields() -> None:
    with pytest.raises(ValueError, match="municipios"):
        parse_emergency_feed("var mapaIndicador = {};")
