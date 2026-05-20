# Gaming Telemetry Service

A real-time telemetry analysis system that ingests player events and detects suspicious behavior like impossible movement speeds by reconstructing player state from timestamped event streams.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.0 (async) · Pydantic v2 · Alembic · APScheduler

---

## Architecture

```
Client
 ↓
API Layer
 ↓
Validation Layer
 ↓
Analysis Layer
(state reconstruction + fraud detection)
 ↓
Persistence Layer
(PostgreSQL)
```

| Layer | Responsibility |
|---|---|
| API | Receives telemetry events and routes requests |
| Validation | Validates schema and required metadata |
| Analysis | Reconstructs player state and detects anomalies |
| Persistence | Stores telemetry events, sessions, and fraud flags |

---

## Key Design Decisions

**State reconstruction inside the analysis layer**
Player state is only reconstructed to support behavioral analysis. Keeping them co-located reduces complexity and keeps the detection pipeline easier to reason about while the system remains focused on event-driven fraud analysis.

**Selective event analysis**
Only a subset of event types are analyzed to keep the fraud detection pipeline focused and avoid unnecessary processing on telemetry that is irrelevant to behavioral analysis.

**Schema validation before analysis**
Events are validated before analysis to ensure malformed or incomplete telemetry does not produce invalid fraud detections or corrupt downstream analysis.

---

## Fraud Detection

The fraud detection system analyzes sequential player movement events within the same session to detect impossible movement speeds. When a new movement event arrives, the analysis layer retrieves the previous movement event, calculates the distance traveled and elapsed time between the two events, and derives the player's movement speed:

v = d / t

If the calculated speed exceeds the configured threshold, the event is flagged as suspicious. Rather than analyzing events in isolation, the system reconstructs player behavior over time using timestamped telemetry data.

---

## API

The API is organized around two core responsibilities: telemetry ingestion and telemetry analytics.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/events` | Ingest a single telemetry event |
| POST | `/events/batch` | Ingest multiple telemetry events |
| GET | `/metrics/dau` | Retrieve daily active user metrics |
| GET | `/metrics/events-by-type` | Retrieve aggregated event counts |
| GET | `/metrics/session-length` | Retrieve session length percentiles |
| GET | `/metrics/flagged-players` | Retrieve flagged players |
| GET | `/metrics/player-risk-score/{player_id}` | Retrieve a player risk score |

**Example Event Payload**

```
POST /events
```

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "player_move",
  "timestamp": "2026-04-01T21:55:38Z",
  "player_id": "player_123",
  "session_id": "session_456",
  "metadata": {
    "position": {
      "x": 125.4,
      "y": 410.2
    }
  }
}
```

Interactive API docs available at `http://localhost:8000/docs` after startup.

---

## Setup

**1. Clone the repository**
```bash
git clone <repo-url>
cd gaming_telemetry_service
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv
```
Windows:
```bash
.venv\Scripts\activate
```
macOS/Linux:
```bash
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file:
```
DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5432/gaming_telemetry
```

**5. Run database migrations**
```bash
alembic upgrade head
```

**6. Start the API server**
```bash
uvicorn app.main:app --reload --port 8000
```

**7. Send a sample telemetry event**
```json
POST /events

{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "player_move",
  "timestamp": "2026-04-01T21:55:38Z",
  "player_id": "player_123",
  "session_id": "session_456",
  "metadata": {
    "position": {
      "x": 125.4,
      "y": 410.2
    }
  }
}
```
