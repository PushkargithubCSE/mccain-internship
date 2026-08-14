"""
Thin repository layer between the routers (HTTP concerns) and the ORM
models. Keeping DB queries here — rather than inline in route handlers —
means the query logic is unit-testable without spinning up FastAPI, and
routers stay focused on request/response shaping and HTTP status codes.
"""
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Inventory, Product, Warehouse

# ---------- Product ----------


async def create_product(db: AsyncSession, **fields) -> Product:
    product = Product(**fields)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> Product | None:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str) -> Product | None:
    result = await db.execute(select(Product).where(Product.sku == sku))
    return result.scalar_one_or_none()


async def list_products(db: AsyncSession, skip: int, limit: int, name_contains: str | None = None):
    query = select(Product)
    count_query = select(func.count()).select_from(Product)
    if name_contains:
        query = query.where(Product.name.ilike(f"%{name_contains}%"))
        count_query = count_query.where(Product.name.ilike(f"%{name_contains}%"))

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(Product.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all(), total


async def update_product(db: AsyncSession, product: Product, fields: dict) -> Product:
    for key, value in fields.items():
        if value is not None:
            setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product: Product) -> None:
    await db.delete(product)  # cascades to inventory_records
    await db.commit()


# ---------- Warehouse ----------


async def create_warehouse(db: AsyncSession, **fields) -> Warehouse:
    warehouse = Warehouse(**fields)
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


async def get_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> Warehouse | None:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    return result.scalar_one_or_none()


async def get_warehouse_by_code(db: AsyncSession, code: str) -> Warehouse | None:
    result = await db.execute(select(Warehouse).where(Warehouse.code == code))
    return result.scalar_one_or_none()


async def list_warehouses(db: AsyncSession, skip: int, limit: int):
    total = (await db.execute(select(func.count()).select_from(Warehouse))).scalar_one()
    result = await db.execute(select(Warehouse).order_by(Warehouse.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all(), total


async def update_warehouse(db: AsyncSession, warehouse: Warehouse, fields: dict) -> Warehouse:
    for key, value in fields.items():
        if value is not None:
            setattr(warehouse, key, value)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


async def delete_warehouse(db: AsyncSession, warehouse: Warehouse) -> None:
    await db.delete(warehouse)  # cascades to inventory_records
    await db.commit()


# ---------- Inventory ----------


async def get_inventory_by_product_and_warehouse(
    db: AsyncSession, product_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Inventory | None:
    result = await db.execute(
        select(Inventory).where(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id)
    )
    return result.scalar_one_or_none()


async def create_inventory(db: AsyncSession, **fields) -> Inventory:
    record = Inventory(**fields)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_inventory(db: AsyncSession, inventory_id: uuid.UUID) -> Inventory | None:
    result = await db.execute(select(Inventory).where(Inventory.id == inventory_id))
    return result.scalar_one_or_none()


async def list_inventory(
    db: AsyncSession,
    skip: int,
    limit: int,
    product_id: uuid.UUID | None = None,
    warehouse_id: uuid.UUID | None = None,
):
    query = select(Inventory)
    count_query = select(func.count()).select_from(Inventory)
    if product_id:
        query = query.where(Inventory.product_id == product_id)
        count_query = count_query.where(Inventory.product_id == product_id)
    if warehouse_id:
        query = query.where(Inventory.warehouse_id == warehouse_id)
        count_query = count_query.where(Inventory.warehouse_id == warehouse_id)

    total = (await db.execute(count_query)).scalar_one()
    result = await db.execute(query.order_by(Inventory.updated_at.desc()).offset(skip).limit(limit))
    return result.scalars().all(), total


async def list_inventory_by_product(db: AsyncSession, product_id: uuid.UUID) -> list[Inventory]:
    """Eager-loads the warehouse on each row so the router can return it inline
    without triggering N+1 lazy-load queries."""
    result = await db.execute(
        select(Inventory).where(Inventory.product_id == product_id).options(selectinload(Inventory.warehouse))
    )
    return list(result.scalars().all())


async def list_inventory_by_warehouse(db: AsyncSession, warehouse_id: uuid.UUID) -> list[Inventory]:
    result = await db.execute(
        select(Inventory).where(Inventory.warehouse_id == warehouse_id).options(selectinload(Inventory.product))
    )
    return list(result.scalars().all())


async def update_inventory(db: AsyncSession, record: Inventory, fields: dict) -> Inventory:
    for key, value in fields.items():
        if value is not None:
            setattr(record, key, value)
    await db.commit()
    await db.refresh(record)
    return record


async def adjust_inventory_quantity(db: AsyncSession, inventory_id: uuid.UUID, delta: int) -> Inventory | None:
    """
    Atomic stock adjustment: `quantity = quantity + delta` executed as a
    single UPDATE ... RETURNING statement, rather than "read quantity in
    Python, compute new value, write it back". The latter is a classic
    lost-update race: two concurrent requests both read qty=10, both
    compute 10-3=7, both write 7 — one decrement is silently lost. Doing
    the arithmetic in the SQL statement means Postgres's row-level locking
    serializes concurrent updates correctly.

    The CHECK (quantity >= 0) constraint on the table is the backstop:
    if a decrement would take stock negative, the DB rejects the write
    rather than allowing an inconsistent state.
    """
    stmt = (
        update(Inventory)
        .where(Inventory.id == inventory_id)
        .values(quantity=Inventory.quantity + delta)
        .returning(Inventory)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    await db.commit()
    return row


async def delete_inventory(db: AsyncSession, record: Inventory) -> None:
    await db.delete(record)
    await db.commit()
