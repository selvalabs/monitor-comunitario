from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from monitor_comunitario.db.models import (
    Base,
    HermesEvent,
    Notification,
    NotificationKind,
    OutageNotice,
    User,
)
from monitor_comunitario.matcher.scoring import MatchLevel, MatchResult
from monitor_comunitario.services.matching import (
    create_app_notification,
    create_resolution_notifications,
    persist_match,
)


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
        hermes_events = list(session.scalars(select(HermesEvent)).all())

    assert first_created is True
    assert second_created is False
    assert first_notification.id == second_notification.id
    assert len(hermes_events) == 1
    assert hermes_events[0].event_type == "notification_ready"
    assert hermes_events[0].channel == "app"
    assert hermes_events[0].recipient_phone == "5548999999999"
    assert hermes_events[0].intent == "ALERT_EXPLANATION"
    assert hermes_events[0].template_key == "alert_explanation_v1"


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


def test_resolution_notification_requires_initial_alert_and_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)

    Base.metadata.create_all(bind=engine)

    with testing_session_local() as session:
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
            description="Comunicado CASAN: rompimento de rede.",
            raw_text="Rompimento de rede.",
            content_hash="resolution",
            is_active=True,
        )
        session.add_all([user, notice])
        session.commit()
        session.refresh(user)
        session.refresh(notice)

        result = MatchResult(MatchLevel.STREET, 100.0, "Street matched.")
        create_app_notification(session, user, notice, result)
        persist_match(session, user, notice, result)
        notice.is_active = False
        notice.resolved_at = notice.created_at
        session.commit()

        first_created = create_resolution_notifications(session, notice)
        second_created = create_resolution_notifications(session, notice)
        notifications = list(session.scalars(select(Notification)).all())
        resolution_events = list(
            session.scalars(
                select(HermesEvent).where(HermesEvent.payload_json.contains("resolution"))
            ).all()
        )

    assert first_created == 1
    assert second_created == 0
    assert len(notifications) == 2
    assert {item.notification_kind for item in notifications} == {
        NotificationKind.ALERT.value,
        NotificationKind.RESOLUTION.value,
    }
    assert len(resolution_events) == 1
