from datetime import datetime, timezone

import pytest
from app.models.player_flag import Playerflag
from app.services.aggregation import get_flagged_player


@pytest.mark.asyncio
async def test_flagged_player_cursor_handles_same_timestamp(db_session):

    timestamp = datetime(2026, 5, 14, 13, 21, tzinfo=timezone.utc)

    flags = [
        Playerflag(
            player_id="player_1",
            flag_type="speed_hack",
            severity="critical",
            timestamp=timestamp,
            context={},
            status="open",
        ),
        Playerflag(
            player_id="player_2",
            flag_type="score_hack",
            severity="high",
            timestamp=timestamp,
            context={},
            status="open",
        ),
        Playerflag(
            player_id="player_3",
            flag_type="bot",
            severity="medium",
            timestamp=timestamp,
            context={},
            status="open",
        ),
    ]

    db_session.add_all(flags)
    await db_session.commit()

    first_page = await get_flagged_player(
        db_session,
        limit=2,
    )

    assert len(first_page.items) == 2
    assert first_page.next_cursor_timestamp is not None
    assert first_page.next_cursor_flag_id is not None

    second_page = await get_flagged_player(
        db_session,
        cursor_timestamp=first_page.next_cursor_timestamp,
        cursor_flag_id=first_page.next_cursor_flag_id,
        limit=2,
    )

    assert len(second_page.items) == 1

@pytest.mark.asyncio
async def test_flagged_player_rejects_partial_cursor(async_client):

    response = await async_client.get(
        "/v1/metrics/flagged-players",
        params={
            "cursor_timestamp": "2026-05-14T13:21:00Z",
        },
    )

    assert response.status_code == 400