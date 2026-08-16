from monitor_comunitario.scraper.casan_alerts import (
    CasanWaterAlert,
    parse_casan_alerts_html,
)

HTML = """
<table>
  <tr><th>Notificado em</th><th>Problema</th></tr>
  <tr>
    <td>16/08/2026 10:30</td>
    <td>
      Município(s): São José<br>
      Bairro(s): Barreiros e Serraria<br>
      Rua(s): Todos<br>
      Ocorrência: Rompimento de rede de distribuição. O fornecimento ficará prejudicado.
      Previsão de normalização até 18:00.
    </td>
  </tr>
  <tr>
    <td>16/08/2026 08:00</td>
    <td>
      Município(s): Florianópolis<br>
      Bairro(s): Lagoa da Conceição<br>
      Rua(s): Avenida das Rendeiras<br>
      Ocorrência: O conserto foi concluído e o sistema foi aberto. O abastecimento
      está em recuperação gradual.
    </td>
  </tr>
</table>
"""


def test_parse_casan_alerts_extracts_location_and_occurrence() -> None:
    assert parse_casan_alerts_html(HTML) == [
        CasanWaterAlert(
            notified_at="16/08/2026 10:30",
            municipality="São José",
            neighborhood="Barreiros e Serraria",
            street="Todos",
            occurrence=(
                "Rompimento de rede de distribuição. O fornecimento ficará "
                "prejudicado. Previsão de normalização até 18:00."
            ),
            raw_text=(
                "Município(s): São José Bairro(s): Barreiros e Serraria "
                "Rua(s): Todos Ocorrência: Rompimento de rede de distribuição. "
                "O fornecimento ficará prejudicado. Previsão de normalização "
                "até 18:00."
            ),
            normalization_confirmed=False,
        ),
        CasanWaterAlert(
            notified_at="16/08/2026 08:00",
            municipality="Florianópolis",
            neighborhood="Lagoa da Conceição",
            street="Avenida das Rendeiras",
            occurrence=(
                "O conserto foi concluído e o sistema foi aberto. "
                "O abastecimento está em recuperação gradual."
            ),
            raw_text=(
                "Município(s): Florianópolis Bairro(s): Lagoa da Conceição "
                "Rua(s): Avenida das Rendeiras Ocorrência: O conserto foi concluído "
                "e o sistema foi aberto. O abastecimento está em recuperação gradual."
            ),
            normalization_confirmed=True,
        ),
    ]


def test_parse_casan_alerts_ignores_headers_and_unrelated_rows() -> None:
    html = "<table><tr><th>Notificado em</th></tr><tr><td>sem ocorrência</td></tr></table>"

    assert parse_casan_alerts_html(html) == []
