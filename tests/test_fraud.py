import pytest
from sqlalchemy import select
from app.models.player_flag import Playerflag
from asyncio import sleep
import uuid

@pytest.mark.asyncio
async def test_impossible_movement_false_negative(async_client, db_session):
    player_id = "player_99"
    session_id = "sess_001"

    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:00Z",
        "metadata": { "position": {"x": 10.0, "y": 10.0}},
        "event_data": {}
        
    }

    resp1 = await async_client.post("/v1/events", json=payload)
    assert resp1.status_code == 201

    hacked_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:01Z",
        "metadata": {
            "position": {"x": 5000.0, "y": 5000.0}
        },
        "event_data": {}
    }
    resp2 = await async_client.post("/v1/events", json=hacked_payload)
    assert resp2.status_code == 201

    await sleep(0.1)

    result = await db_session.execute(
        select(Playerflag).where(Playerflag.player_id == player_id)
    )
    flag = result.scalar_one_or_none()

    assert flag is not None, "Speed hack flag not generated"
    assert flag.flag_type == "speed_hack"
    assert flag.severity == "critical"
    assert flag.status == "open"

@pytest.mark.asyncio
async def test_false_positive_normal_movement(async_client, db_session):
    player_id = "player_legit"
    session_id = "sess_002"

    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:00Z",
        "metadata": {
            "position": {"x": 10.0, "y": 10.0}
          },
        "event_data": {}
      }

    resp1 = await async_client.post("/v1/events", json=payload)
    assert resp1.status_code == 201

    normal_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:02Z",
        "metadata": {
             "position": {"x": 16.0, "y": 18.0},
        },
        "event_data": {}
    }
    resp2 = await async_client.post("/v1/events", json=normal_payload)
    assert resp2.status_code == 201

    await sleep(0.1)

    result = await db_session.execute(
        select(Playerflag).where(Playerflag.player_id == player_id)
    )
    flag = result.scalar_one_or_none()

    assert flag is None,  "Incorrectly flagged"

@pytest.mark.asyncio
async def test_score_hack_detected(async_client, db_session):
    player_id = "player_hacker"
    session_id = "sess_score_001"

    session_start_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "session_start",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:00Z",
        "metadata": {},
        "event_data": {}
    }

    resp1 = await async_client.post("/v1/events", json=session_start_payload)
    assert resp1.status_code == 201

    score_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "score_update",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:02Z",
        "metadata": {
             "score": 10000
        },
        "event_data": {}
    }
    resp2 = await async_client.post("/v1/events", json=score_payload)
    assert resp2.status_code == 201

    await sleep(0.1)

    result = await db_session.execute(
        select(Playerflag).where(Playerflag.player_id == player_id)
    )
    flag = result.scalar_one_or_none()

    assert flag is not None, "Flag was not generated"
    assert flag.flag_type == "score_hack"
    assert flag.severity == "critical"
    assert flag.status == "open"

@pytest.mark.asyncio
async def test_evasion_attack(async_client, db_session):
    player_id = "player_evasion_hacker"
    session_id = "sess_evade_001"

    session_start_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "session_start",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:00Z",
        "metadata": {},
        "event_data": {}
    }

    resp_start = await async_client.post("/v1/events", json=session_start_payload)
    assert resp_start.status_code == 201

    move_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:01Z",
        "metadata": {
            "position": {"x": 0.0, "y": 0.0}
        },
        "event_data": {}
    }
    resp_move1 = await async_client.post("/v1/events", json=move_payload)
    assert resp_move1.status_code == 201

    evade_speed_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "player_move",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:02Z",
        "metadata": {
            "position": {"x": 999.0, "y": 0.0}
        },
        "event_data": {}
    }
    resp_move2 = await async_client.post("/v1/events", json=evade_speed_payload)
    assert resp_move2.status_code == 201

    evade_score_payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": "score_update",
        "player_id": player_id,
        "session_id": session_id,
        "timestamp": "2026-05-14T13:21:03Z",
        "metadata":{
            "score": 5997
        },
        "event_data": {}
    }
    resp_score = await async_client.post("/v1/events", json=evade_score_payload)
    assert resp_score.status_code == 201

    await sleep(0.1)

    result = await db_session.execute(
        select(Playerflag).where(Playerflag.player_id == player_id)
    )
    flag = result.scalar_one_or_none()

    assert flag is None, f"System caught user with a '{flag.flag_type}' flag."