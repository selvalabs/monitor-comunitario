from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from monitor_comunitario.db.models import Base
from monitor_comunitario.scraper.celesc_emergency import EmergencyOutage
from monitor_comunitario.scraper.parser import ParsedOutageNotice
from monitor_comunitario.services.outage_notices import (
    build_notice_content_hash,
    persist_emergency_outages,
    persist_parsed_notice,
)


def test_build_notice_content_hash_is_stable() -> None:
    notice = ParsedOutageNotice(
        municipality="Florianópolis",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        description="Manutenção preventiva.",
        raw_text="FLORIANÓPOLIS\nBairro: Campeche\nMotivo: Manutenção preventiva.",
    )

    first_hash = build_notice_content_hash(notice, "https://example.com")
    second_hash = build_notice_content_hash(notice, "https://example.com")

    assert first_hash == second_hash


def test_persist_parsed_notice_deduplicates_by_hash() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)

    Base.metadata.create_all(bind=engine)

    parsed_notice = ParsedOutageNotice(
        municipality="Florianópolis",
        neighborhood="Campeche",
        street="Avenida Pequeno Príncipe",
        description="Manutenção preventiva.",
        raw_text="FLORIANÓPOLIS\nBairro: Campeche\nMotivo: Manutenção preventiva.",
    )

    with testing_session_local() as session:
        first_notice, first_created = persist_parsed_notice(
            session=session,
            parsed_notice=parsed_notice,
            source_url="https://example.com",
        )

        second_notice, second_created = persist_parsed_notice(
            session=session,
            parsed_notice=parsed_notice,
            source_url="https://example.com",
        )

    assert first_created is True
    assert second_created is False
    assert first_notice.id == second_notice.id


def test_persist_emergency_outages_updates_and_resolves_by_locality() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    outage = EmergencyOutage(
        municipality="Florianopolis",
        municipality_id=1101,
        neighborhood="Trindade",
        neighborhood_id=59,
        affected_units=12,
        total_units=12,
        raw_text="Florianopolis / Trindade",
    )

    with testing_session_local() as session:
        first, first_created = persist_emergency_outages(
            session, [outage], "https://celgeoweb.celesc.com.br/json/tabelas.js"
        )
        outage_updated = EmergencyOutage(
            **{**outage.__dict__, "affected_units": 9}
        )
        second, second_created = persist_emergency_outages(
            session, [outage_updated], "https://celgeoweb.celesc.com.br/json/tabelas.js"
        )
        persist_emergency_outages(
            session, [], "https://celgeoweb.celesc.com.br/json/tabelas.js"
        )

    assert first_created == 1
    assert second_created == 0
    assert first[0].id == second[0].id
    assert second[0].description.startswith("Ocorrência emergencial: 9")
    assert second[0].is_active is False
    assert second[0].resolved_at is not None
