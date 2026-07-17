from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from monitor_comunitario.db.models import Base, OutageNotice, User
from monitor_comunitario.matcher.scoring import MatchLevel, MatchResult
from monitor_comunitario.services.matching import create_app_notification, persist_match


def test_create_app_notification_deduplicates_by_user_notice_channel() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)

    Base.metadata.create_all(bind=engine)

    with testing_session_local() as session:
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

        session.add(user)
        session.add(notice)
        session.commit()
        session.refresh(user)
        session.refresh(notice)

        result = MatchResult(
            level=MatchLevel.STREET,
            score=100.0,
            reason="Street matched.",
        )

        first_notification, first_created = create_app_notification(session, user, notice, result)
        second_notification, second_created = create_app_notification(session, user, notice, result)

    assert first_created is True
    assert second_created is False
    assert first_notification.id == second_notification.id


def test_persist_match_deduplicates_by_user_notice() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)

    Base.metadata.create_all(bind=engine)

    with testing_session_local() as session:
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

        session.add(user)
        session.add(notice)
        session.commit()
        session.refresh(user)
        session.refresh(notice)

        result = MatchResult(
            level=MatchLevel.STREET,
            score=100.0,
            reason="Street matched.",
        )

        first_match, first_created = persist_match(session, user, notice, result)
        second_match, second_created = persist_match(session, user, notice, result)

    assert first_created is True
    assert second_created is False
    assert first_match.id == second_match.id
