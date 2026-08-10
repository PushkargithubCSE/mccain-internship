# McCain Identity Service

Central identity & auth microservice for the McCain distributed backend platform.
Backend-only: FastAPI + PostgreSQL + Redis + Docker, with JWT auth and a
Redis-backed sliding-window rate limiter. Kafka and gRPC are included as
optional, toggleable pieces that make sense for a multi-service platform.

## Why these pieces

| Concern | Choice | Why |
|---|---|---|
| REST API | FastAPI | External-facing auth flows (register/login/refresh) — human/browser/mobile clients need HTTP+JSON. |
| Data store | PostgreSQL | Users and refresh tokens are relational, need ACID guarantees and foreign keys (e.g. cascade-delete a user's tokens). |
| Rate limiting & ephemeral state | Redis | Sub-millisecond atomic counters; sliding-window rate limits, account lockout counters, access-token blacklist. |
| Internal service-to-service auth | gRPC | Every other microservice on the platform will call "is this token valid" on the hot path of *every* authenticated request — gRPC's binary protocol + HTTP/2 multiplexing beats REST for that volume/latency profile. |
| Cross-service events | Kafka (Redpanda) | Other services (notifications, audit, CRM sync) need to react to `user.registered`, `user.login`, `user.password_changed` without being coupled to this service via synchronous REST calls. |

Both Kafka and gRPC are fully toggleable via `KAFKA_ENABLED` / `GRPC_ENABLED`
env vars if you want a leaner deployment.

## Architecture

```
                         ┌─────────────────────────┐
  Browser / Mobile ────► │   FastAPI (REST, :8000)  │
                         │   /api/v1/auth/*          │
                         │   /api/v1/users/*          │
                         │   /health*                  │
                         └─────────┬──────────┬───────┘
                                   │          │
                     ┌─────────────┘          └──────────────┐
                     ▼                                       ▼
            ┌──────────────┐                        ┌──────────────┐
            │  PostgreSQL   │                        │     Redis     │
            │  users,       │                        │  rate limits, │
            │  refresh_tok  │                        │  lockouts,    │
            └──────────────┘                        │  token         │
                                                      │  blacklist     │
                                                      └──────────────┘
                     │
                     ▼
            ┌──────────────┐        ┌───────────────────────────┐
            │ Kafka/Redpanda│◄───────┤ user.registered/login/... │
            └──────────────┘        └───────────────────────────┘

  Other microservices ───► gRPC (:50051) VerifyToken / GetUser
```

## Auth design

- **Access token**: JWT, 15 min TTL, stateless (verified by signature only).
  Carries `sub` (user id), `role`, `type=access`, `jti`.
- **Refresh token**: JWT, 7 day TTL, `type=refresh`, unique `jti` persisted
  in Postgres (`refresh_tokens` table). Every `/auth/refresh` call **rotates**
  the token: the old `jti` is marked revoked and a brand-new pair is issued.
  This means a stolen-and-replayed refresh token can be used at most once,
  and rotation gives you a natural "this session was hijacked" signal (two
  parties trying to use the same revoked token).
- **Logout**: revokes a specific refresh token, or all of a user's tokens
  (`all_devices: true`).
- **Password change**: revokes *all* refresh tokens for that user, forcing
  re-auth everywhere else.
- **Account lockout**: 5 failed login attempts within 15 minutes locks the
  account (Redis counter, independent of the rate limiter).

## Rate limiting design

Redis sorted-set sliding-window log, executed atomically via a Lua script
(race-free under concurrent requests, no separate cleanup job needed since
keys carry a TTL). Two layers:

1. **Global** (ASGI middleware): every request, per client IP, default
   100 req/60s.
2. **Per-route** (FastAPI dependency): tighter buckets on sensitive
   endpoints — login (5/60s), register (3/60s) — independent of the global
   bucket, so brute-forcing login can't hide inside the general traffic
   allowance.

Every response carries `X-RateLimit-Limit` / `X-RateLimit-Remaining`
headers; a 429 carries `Retry-After`.

## Project layout

```
app/
  main.py                 FastAPI app, lifespan (redis/kafka/grpc startup)
  config.py                Pydantic settings (env-driven)
  database.py               Async SQLAlchemy engine/session
  redis_client.py            Shared async Redis client
  models/user.py               User, RefreshToken ORM models
  schemas/auth.py                Pydantic request/response models
  core/security.py                 bcrypt hashing, JWT issue/verify
  core/rate_limiter.py               Redis sliding-window limiter (Lua)
  middleware/rate_limit_middleware.py  Global per-IP limiter
  api/deps.py                            DB/redis/current-user/rate-limit deps
  api/v1/auth.py                           register/login/refresh/logout/me
  api/v1/users.py                            admin user management (RBAC)
  api/v1/health.py                             liveness/readiness probes
  events/kafka_producer.py                       user.* event publishing
  grpc_server/                                     proto + generated pb2 + server
alembic/                    DB migrations
docker-compose.yml            postgres + redis + redpanda + app
Dockerfile
```

## Running it

```bash
cp .env.example .env      # adjust JWT_SECRET_KEY at minimum
docker compose up --build
```

This brings up Postgres, Redis, Redpanda (Kafka API), runs migrations via
the one-shot `migrate` service, then starts the app on:

- REST API: `http://localhost:8000` (docs at `/docs`)
- gRPC: `localhost:50051`

To run migrations manually against a running stack:
```bash
docker compose run --rm migrate
```

To run locally without Docker (needs local Postgres/Redis):
```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## API summary

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | – | rate-limited 3/60s |
| POST | `/api/v1/auth/login` | – | rate-limited 5/60s, account lockout |
| POST | `/api/v1/auth/refresh` | refresh token | rotates the token |
| POST | `/api/v1/auth/logout` | access token | revoke one or all sessions |
| GET | `/api/v1/auth/me` | access token | current user |
| POST | `/api/v1/auth/change-password` | access token | revokes all sessions |
| GET | `/api/v1/users` | admin | list users |
| GET | `/api/v1/users/{id}` | admin | get user |
| PATCH | `/api/v1/users/{id}/deactivate` | admin | deactivate |
| GET | `/health`, `/health/live`, `/health/ready` | – | probes |

gRPC (`app/grpc_server/identity.proto`): `VerifyToken(access_token)`,
`GetUser(user_id)` — for other platform services to call internally.

## What's deliberately out of scope

- Email verification / password reset delivery (the `is_verified` flag and
  hooks are there; wiring an email provider is a platform-specific choice).
- OAuth2/social login providers.
- Full test suite (endpoints were manually smoke-tested end-to-end against
  real Postgres/Redis during development — see notes below — but no pytest
  suite is included; happy to add one if useful).

## Verified during development

Before delivery this was actually run — not just written — against real
Postgres and Redis: migrations applied cleanly, and the full flow
(register → duplicate/weak-password rejection → login → wrong-password
lockout → `/me` with/without/garbage token → refresh rotation → replay
rejection → RBAC 403 for non-admins → logout → revoked-token rejection →
per-route rate-limit 429) all passed. Two real bugs were caught and fixed
this way: a `passlib`/`bcrypt` version incompatibility, and a Postgres enum
value mismatch between SQLAlchemy and the migration.
