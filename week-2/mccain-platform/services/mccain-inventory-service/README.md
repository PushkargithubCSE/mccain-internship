# McCain Inventory Service

Products, warehouses, and per-warehouse stock levels. Kept intentionally
simple: FastAPI + PostgreSQL + Docker, no auth/messaging layer of its own
(in the real platform it would sit behind the identity service's gRPC
token verification, but that's left out here to keep this service focused).

## Schema

```
Product  1 ──< Inventory >── 1  Warehouse
```

`Inventory` is an **association object**: a product can be stocked in many
warehouses and a warehouse holds many products, so it's a many-to-many —
but since the relationship itself needs an attribute (`quantity`), a plain
`secondary=` join table isn't enough. `Inventory` is modeled as its own
table with FKs to both sides plus its own columns. This is the standard
pattern any time a many-to-many needs metadata (think: enrollments with a
grade, order line items with a quantity and price, etc.).

Constraints doing real work here (not just decoration):
- `UniqueConstraint(product_id, warehouse_id)` — one stock row per
  product per warehouse, enforced by the DB, not application logic.
- `CheckConstraint(quantity >= 0)` — stock can never go negative, even if
  application code has a bug.
- `ON DELETE CASCADE` on both FKs — deleting a product or warehouse
  cleans up its stock rows automatically; verified in testing (deleting a
  warehouse removed only *that* warehouse's inventory row, leaving the
  same product's stock in other warehouses untouched).

## The interesting endpoint: atomic stock adjustment

`POST /inventory/{id}/adjust` with `{"delta": -5}` does the arithmetic in
the SQL statement itself:

```sql
UPDATE inventory SET quantity = quantity + :delta WHERE id = :id RETURNING *;
```

rather than "read quantity → compute new value in Python → write it
back", which is a classic lost-update race: two concurrent requests both
read qty=10, both compute 7, both write 7 — one decrement vanishes.
Postgres's row-level locking serializes the SQL-side update correctly.

This was verified for real, not just argued: firing 20 concurrent `-1`
adjustments at the same row landed on exactly `starting_qty - 20`, with
no lost updates. The `CHECK (quantity >= 0)` constraint is the backstop —
an adjustment that would take stock negative is rejected with a 409
rather than silently corrupting state.

## Project layout

```
app/
  main.py         FastAPI app + health checks
  config.py        env-driven settings
  database.py        async SQLAlchemy engine/session
  models.py            Product, Warehouse, Inventory (association object)
  schemas.py              Pydantic request/response models
  crud.py                   repository layer (DB queries, no HTTP concerns)
  routers/
    products.py               product CRUD + GET /products/{id}/inventory
    warehouses.py               warehouse CRUD + GET /warehouses/{id}/inventory
    inventory.py                  stock CRUD + POST /inventory/{id}/adjust
alembic/            migrations
docker-compose.yml
Dockerfile
```

Why a `crud.py` layer instead of querying the DB straight in the routers:
keeps route handlers focused on HTTP concerns (status codes, request
validation), and the query logic is unit-testable without spinning up
FastAPI at all.

## Running it

```bash
cp .env.example .env
docker compose up --build
```

Runs on `http://localhost:8001` (docs at `/docs`). Uses host port 5433 for
its own Postgres so it can run alongside the identity service's Postgres
(port 5432) without colliding.

Locally without Docker:
```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

## API summary

| Method | Path | Notes |
|---|---|---|
| POST/GET | `/products` | create / paginated list (`?name=` filter) |
| GET/PUT/DELETE | `/products/{id}` | cascade-deletes its inventory rows |
| GET | `/products/{id}/inventory` | stock across every warehouse |
| POST/GET | `/warehouses` | create / paginated list |
| GET/PUT/DELETE | `/warehouses/{id}` | cascade-deletes its inventory rows |
| GET | `/warehouses/{id}/inventory` | every product stocked there |
| POST/GET | `/inventory` | create stock record / list (`?product_id=`, `?warehouse_id=` filters) |
| GET/PUT/DELETE | `/inventory/{id}` | PUT overwrites quantity to an absolute value |
| POST | `/inventory/{id}/adjust` | atomic relative change (`{"delta": n}`) |

## Verified during development

Ran against a real local Postgres (not just imported/linted): created
warehouses and a product, stocked the same product in two warehouses,
confirmed both directional relationship queries return correctly,
exercised `/adjust` for increments/decrements, confirmed a would-go-negative
adjustment is rejected with 409 and leaves state unchanged, fired 20
genuinely concurrent adjustments at one row and got the mathematically
correct result, and confirmed cascade delete removes only the affected
warehouse's stock row while a sibling warehouse's stock for the same
product survives untouched.

## Interview talking points this design supports

- Association object vs. plain `secondary=` many-to-many, and when you
  need the former.
- Lost-update race conditions and why "read-modify-write in application
  code" is unsafe under concurrency; how an atomic `UPDATE ... SET x = x + delta`
  sidesteps it via row-level locking.
- Enforcing invariants at the DB layer (`CHECK`, `UNIQUE`, `ON DELETE CASCADE`)
  vs. only in application code — DB constraints are your last line of
  defense against bugs, not just validation UX.
- UUID vs. auto-increment PKs: UUIDs avoid ID collisions if this service's
  data is ever merged/replicated with another (consistent with the
  identity service), at the cost of larger indexes and no natural insert
  ordering.
