# Hermes Events Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal, internal Hermes event bootstrap so Monitor Comunitario can record deterministic notification/support/observability events without external delivery.

**Architecture:** Add a persisted `hermes_events` audit table, deterministic intent/template constants, and a focused service for creating events. The first implementation does not send WhatsApp, Telegram, webhooks, or LLM calls.

**Tech Stack:** Python 3.12, SQLAlchemy 2, Alembic, Pytest, Ruff, Mypy.

---

### Task 1: Deterministic Catalog

**Files:**
- Create: `src/monitor_comunitario/services/hermes_catalog.py`
- Test: `tests/unit/test_hermes_catalog.py`

- [ ] **Step 1: Write failing tests**

```python
from monitor_comunitario.services.hermes_catalog import (
    HERMES_EVENT_TYPES,
    HERMES_ESCALATION_EVENTS,
    HERMES_TEMPLATES,
    UserFacingIntent,
    get_template,
)


def test_user_facing_intents_include_issue_37_initial_scope() -> None:
    assert UserFacingIntent.HELP.value == "HELP"
    assert UserFacingIntent.DELETE_DATA_REQUEST.value == "DELETE_DATA_REQUEST"
    assert UserFacingIntent.UNKNOWN_ESCALATE.value == "UNKNOWN_ESCALATE"


def test_templates_are_deterministic_and_versioned() -> None:
    template = get_template("alert_explanation_v1")

    assert template.intent == UserFacingIntent.ALERT_EXPLANATION
    assert template.user_facing is True
    assert template.llm_allowed is False
    assert "{municipality}" in template.body


def test_catalog_contains_operational_event_types() -> None:
    assert "notification_ready" in HERMES_EVENT_TYPES
    assert "scraper_failed" in HERMES_ESCALATION_EVENTS
    assert "human_escalation_v1" in HERMES_TEMPLATES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_hermes_catalog.py -q`
Expected: FAIL because `monitor_comunitario.services.hermes_catalog` does not exist.

- [ ] **Step 3: Implement minimal catalog**

Create enums/constants/dataclasses for user-facing intents, templates, event types, and escalation event names. Keep template text deterministic and mark all user-facing templates as `llm_allowed=False`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_hermes_catalog.py -q`
Expected: PASS.

### Task 2: Hermes Event Persistence

**Files:**
- Modify: `src/monitor_comunitario/db/models.py`
- Create: `migrations/versions/20260724_0003_hermes_events.py`
- Test: `tests/unit/test_hermes_events.py`

- [ ] **Step 1: Write failing tests**

```python
from monitor_comunitario.db.models import HermesEvent, HermesEventStatus, utc_now


def test_hermes_event_model_records_auditable_payload() -> None:
    event = HermesEvent(
        event_type="notification_ready",
        status=HermesEventStatus.CREATED.value,
        channel="app",
        recipient_phone="+5548999999999",
        intent="ALERT_EXPLANATION",
        template_key="alert_explanation_v1",
        payload_json='{"municipality":"Florianopolis"}',
        source="monitor_comunitario",
    )

    assert event.event_type == "notification_ready"
    assert event.status == "created"
    assert event.llm_allowed is False
    assert event.payload_json == '{"municipality":"Florianopolis"}'


def test_hermes_event_status_values_are_explicit() -> None:
    assert HermesEventStatus.CREATED.value == "created"
    assert HermesEventStatus.QUEUED.value == "queued"
    assert HermesEventStatus.PROCESSED.value == "processed"
    assert HermesEventStatus.FAILED.value == "failed"
    assert HermesEventStatus.ESCALATED.value == "escalated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_hermes_events.py -q`
Expected: FAIL because `HermesEvent` and `HermesEventStatus` do not exist.

- [ ] **Step 3: Implement model and migration**

Add `HermesEventStatus` and `HermesEvent` to `models.py`. Add Alembic migration creating `hermes_events` with audit fields and indexes for status, event type, and created timestamp.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_hermes_events.py -q`
Expected: PASS.

### Task 3: Hermes Event Service

**Files:**
- Create: `src/monitor_comunitario/services/hermes_events.py`
- Test: `tests/unit/test_hermes_event_service.py`

- [ ] **Step 1: Write failing tests**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import Base, HermesEventStatus
from monitor_comunitario.services.hermes_events import create_hermes_event


def test_create_hermes_event_persists_created_event() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        event = create_hermes_event(
            session=session,
            event_type="notification_ready",
            channel="app",
            recipient_phone="+5548999999999",
            intent="ALERT_EXPLANATION",
            template_key="alert_explanation_v1",
            payload={"municipality": "Florianopolis"},
        )

        assert event.id is not None
        assert event.status == HermesEventStatus.CREATED.value
        assert event.llm_allowed is False
        assert '"municipality":"Florianopolis"' in event.payload_json


def test_create_hermes_event_rejects_user_facing_llm() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            create_hermes_event(
                session=session,
                event_type="notification_ready",
                channel="whatsapp",
                recipient_phone="+5548999999999",
                intent="HELP",
                template_key="explain_project_v1",
                payload={},
                llm_allowed=True,
            )
        except ValueError as exc:
            assert "LLM is not allowed for user-facing Hermes templates" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_hermes_event_service.py -q`
Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement service**

Create `create_hermes_event()` to validate template policy, JSON-serialize payload deterministically, persist `HermesEvent`, commit, refresh, and return it.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_hermes_event_service.py -q`
Expected: PASS.

### Task 4: Verification

**Files:**
- No new code files.

- [ ] **Step 1: Run focused tests**

Run: `uv run pytest tests/unit/test_hermes_catalog.py tests/unit/test_hermes_events.py tests/unit/test_hermes_event_service.py -q`
Expected: PASS.

- [ ] **Step 2: Run project quality checks**

Run:
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

Expected: all pass.
