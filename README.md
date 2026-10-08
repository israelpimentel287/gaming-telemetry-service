# Gaming Telemetry Service

A real-time gaming telemetry backend that ingests timestamped player events and detects suspicious behavior such as impossible movement speeds, abnormal scoring rates, and bot-like activity.

Built to demonstrate asynchronous API design, PostgreSQL data modeling, event analysis, fraud detection, background processing, and database performance considerations.

## Tech Stack

* **Python**
* **FastAPI** — asynchronous REST API
* **Pydantic** — request validation and serialization
* **SQLAlchemy 2.0** — asynchronous database access
* **PostgreSQL** — persistent event and fraud data
* **asyncpg** — PostgreSQL async driver
* **Alembic** — database migrations
* **APScheduler** — scheduled cohort statistics
* **pytest** — automated testing

## Architecture

```text
Client
  │
  ▼
FastAPI API
  │
  ├── Validation
  ├── Event Ingestion
  └── Background Fraud Analysis
          │
          ├── Movement Analysis
          ├── Score-Rate Analysis
          ├── Statistical Analysis
          └── Bot Detection
                  │
                  ▼
             PostgreSQL
```

### Layer Responsibilities

| Layer       | Responsibility                                              |
| ----------- | ----------------------------------------------------------- |
| API         | Receives telemetry events and exposes metrics               |
| Validation  | Validates incoming event structure and values               |
| Analysis    | Reconstructs player state and evaluates suspicious behavior |
| Persistence | Stores events, flags, and cohort statistics                 |
| Scheduler   | Periodically calculates cohort statistics                   |

## Event Processing

The service accepts timestamped player events and stores them in PostgreSQL.

Supported event types:

* `player_move`
* `score_update`
* `session_start`
* `session_end`

Example:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "player_move",
  "timestamp": "2026-01-01T12:00:00Z",
  "player_id": "player_123",
  "session_id": "session_456",
  "metadata": {
    "position": {
      "x": 120,
      "y": 340
    }
  }
}
```

After validation and persistence, eligible events are analyzed for suspicious behavior.

## Fraud Detection

The service evaluates multiple signals rather than relying on a single rule.

### Impossible Movement

For movement events, the service finds the player's previous movement within the same session and calculates:

```text
distance / elapsed time = movement speed
```

Movement exceeding the configured threshold can generate a fraud flag.

### Abnormal Score Rate

Score updates are compared against the time elapsed since the player's session started.

An unusually high score-per-second rate can indicate suspicious behavior.

### Statistical Anomaly Detection

The service periodically calculates cohort statistics and uses them to identify unusually large deviations from the normal population.

```text
z-score = (value - mean) / standard deviation
```

If sufficient cohort statistics are unavailable, the statistical check is skipped.

### Bot Detection

Recent player activity is examined for unusually consistent timing patterns.

The check also accounts for insufficient variation in event intervals to avoid flagging players when there is not enough data.

## Duplicate Event Handling

Telemetry systems can receive the same event more than once.

`event_id` is used as the database primary key, allowing PostgreSQL to enforce uniqueness even when concurrent requests attempt to insert the same event.

Duplicate insertion attempts are handled through `IntegrityError` handling rather than relying only on a preliminary existence check.

## Background Fraud Analysis

Event ingestion and fraud analysis are separated.

The API validates and persists the incoming event, then schedules eligible fraud analysis as a FastAPI background task.

This keeps the ingestion path focused on accepting valid telemetry while allowing analysis to happen after the response has been prepared.

## Database Design

The service uses PostgreSQL with asynchronous SQLAlchemy.

### `game_events`

Stores incoming telemetry events.

Key fields include:

* `event_id`
* `event_type`
* `player_id`
* `session_id`
* `timestamp`
* `event_data` (`JSONB`)

Indexes support common player- and timestamp-based queries.

### `player_flag`

Stores detected suspicious behavior.

Key fields include:

* `flag_id`
* `player_id`
* `flag_type`
* `severity`
* `timestamp`
* `context`
* `status`

Required fields are enforced at the database level.

### `cohort_stats`

Stores periodically calculated statistics used by statistical fraud detection.

## Metrics API

| Endpoint                            | Purpose                      |
| ----------------------------------- | ---------------------------- |
| `GET /v1/metrics/dau`               | Daily active users           |
| `GET /v1/metrics/events-by-type`    | Event counts grouped by type |
| `GET /v1/metrics/session-length`    | Session-duration metrics     |
| `GET /v1/metrics/flagged-players`   | Cursor-paginated fraud flags |
| `GET /v1/metrics/player-risk-score` | Player risk analysis         |

Flag pagination uses a stable ordering:

```text
timestamp DESC
flag_id DESC
```

This keeps pagination deterministic when multiple flags share the same timestamp.

## Health Check

```text
GET /health
```

The endpoint verifies database connectivity with:

```sql
SELECT 1
```

A successful connection returns:

```json
{
  "status": "healthy"
}
```

Database failures return HTTP `503`.

## Testing

The project uses `pytest` for automated testing.

Tests use a dedicated database configuration rather than the development database.

Run the test suite with:

```bash
pytest
```

## Database Migrations

Alembic manages database schema changes.

```bash
alembic upgrade head
```

Migrations cover the initial schema as well as later changes such as telemetry JSON data, indexes, cohort statistics, and database constraints.

## Running Locally

### 1. Clone

```bash
git clone https://github.com/israelpimentel287/gaming-telemetry-service.git
cd gaming-telemetry-service
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure PostgreSQL

Set the database connection through the environment:

```text
DATABASE_URL=postgresql+asyncpg://user:password@localhost/gaming_telemetry
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the application

```bash
uvicorn app.main:app --reload
```
