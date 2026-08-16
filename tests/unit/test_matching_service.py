from monitor_comunitario.db.models import OutageNotice, User
from monitor_comunitario.matcher.scoring import MatchLevel, MatchResult
from monitor_comunitario.services.matching import build_notification_message, match_user_to_notice


def test_match_user_to_notice_by_street() -> None:
    user = User(
        name="Carlos",
        phone="5548999999999",
        municipality="Florianópolis",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        notifications_approved=True,
    )
    notice = OutageNotice(
        source_url="https://example.com",
        municipality="FLORIANOPOLIS",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        description="Manutenção preventiva.",
        raw_text="Bairro: Campeche\nRua: Avenida Pequeno Príncipe",
        content_hash="abc",
    )

    result = match_user_to_notice(user, notice)

    assert result.level == MatchLevel.STREET


def test_match_user_to_notice_by_neighborhood_when_street_missing() -> None:
    user = User(
        name="Carlos",
        phone="5548999999999",
        municipality="Florianópolis",
        neighborhood="Campeche",
        street="",
        notifications_approved=True,
    )
    notice = OutageNotice(
        source_url="https://example.com",
        municipality="FLORIANOPOLIS",
        neighborhood="Campeche",
        street="",
        description="Manutenção preventiva.",
        raw_text="Bairro: Campeche",
        content_hash="abc",
    )

    result = match_user_to_notice(user, notice)

    assert result.level == MatchLevel.NEIGHBORHOOD


def test_match_user_to_notice_returns_none_for_other_municipality() -> None:
    user = User(
        name="Carlos",
        phone="5548999999999",
        municipality="São José",
        neighborhood="Kobrasol",
        street="Rua Koesa",
        notifications_approved=True,
    )
    notice = OutageNotice(
        source_url="https://example.com",
        municipality="FLORIANOPOLIS",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        description="Manutenção preventiva.",
        raw_text="Bairro: Campeche",
        content_hash="abc",
    )

    result = match_user_to_notice(user, notice)

    assert result.level == MatchLevel.NONE


def test_match_user_to_notice_requires_notification_approval() -> None:
    user = User(
        name="Carlos",
        phone="5548999999999",
        municipality="Florianópolis",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        notifications_approved=False,
    )
    notice = OutageNotice(
        source_url="https://example.com",
        municipality="FLORIANOPOLIS",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        description="Manutenção preventiva.",
        raw_text="Bairro: Campeche\nRua: Avenida Pequeno Príncipe",
        content_hash="approval",
    )

    result = match_user_to_notice(user, notice)

    assert result.level == MatchLevel.NONE
    assert result.reason == "User is not approved for notifications."


def test_build_notification_message_identifies_casan_alert() -> None:
    user = User(
        name="Carlos",
        phone="5548999999999",
        municipality="São José",
        neighborhood="Kobrasol",
        street="Rua Koesa",
        notifications_approved=True,
    )
    notice = OutageNotice(
        source="casan",
        notice_type="water",
        source_url="https://e.casan.com.br/avisos/",
        municipality="São José",
        neighborhood="Kobrasol",
        street="Rua Koesa",
        description="Rompimento de rede.",
        raw_text="Rompimento de rede.",
        content_hash="casan",
    )

    title, message = build_notification_message(
        user,
        notice,
        MatchResult(MatchLevel.STREET, 100.0, "street"),
    )

    assert title == "Possível falta de água em São José"
    assert "CASAN" in message
    assert "Rompimento de rede." in message
