import pytest
from sqlalchemy import select
from app.models.event import GameEventModel
import uuid

@pytest.mark.asyncio
async def test_valid_event_stored(async_client, db_session):

    event_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": "player_99",
        "session_id": "sess_001",
        "timestamp": "2026-05-14T13:21:00Z",
        "event_data": {"detected_speed": "150kmh"},
        "metadata": {}
    }

    response = await async_client.post("/v1/events", json=event_payload)
    assert response.status_code == 201

    result = await db_session.execute(
        select(GameEventModel).where(GameEventModel.player_id == "player_99")
    )
    stored_event = result.scalar_one_or_none()

    assert stored_event is not None
    assert stored_event.event_type == "player_move"

@pytest.mark.asyncio
async def test_invalid_evnt_rejected(async_client, db_session):

    invalid_payload = {
        "session_id": "sess_002",
        "timestamp": "2026-05-14T13:21:00Z",
        "event_data": {"broken": "payload"}
    }

    response = await async_client.post("/v1/events", json=invalid_payload)

    assert response.status_code == 422

    result = await db_session.execute(select(GameEventModel))
    stored_events = result.scalars().all()
    assert len(stored_events) == 0

@pytest.mark.asyncio
async def test_duplicate_event_idempotency(async_client, db_session):

    unique_id = str(uuid.uuid4())
    idempotent_payload = {
        "event_id": unique_id,
        "event_type": "score_update",
        "player_id": "player_100",
        "session_id": "sess_777",
        "timestamp": "2026-05-14T13:50:00Z",
        "event_data": {"platform": "PC"},
        "metadata": {}
    }

    first_response = await async_client.post("/v1/events", json=idempotent_payload)
    assert first_response.status_code == 201

    second_response = await async_client.post("/v1/events", json=idempotent_payload)

    assert second_response .status_code in [200, 201, 409]

    result = await db_session.execute(
        select(GameEventModel).where(GameEventModel.event_id == unique_id)
    )

    records = result.scalars().all()
    assert len(records) == 1