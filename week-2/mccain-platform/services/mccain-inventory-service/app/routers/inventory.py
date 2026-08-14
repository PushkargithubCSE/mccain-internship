import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    InventoryAdjust,
    InventoryCreate,
    InventoryListOut,
    InventoryOut,
    InventoryUpdate,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
async def create_inventory(payload: InventoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a stock record linking a product to a warehouse. Fails with 404
    if either side doesn't exist, and 409 if this product/warehouse pair
    already has a stock record (use PUT or /adjust to change quantity instead)."""
    if await crud.get_product(db, payload.product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if await crud.get_warehouse(db, payload.warehouse_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    try:
        return await crud.create_inventory(db, **payload.model_dump())
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory record for this product/warehouse pair already exists",
        )


@router.get("", response_model=InventoryListOut)
async def list_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    product_id: uuid.UUID | None = Query(default=None),
    warehouse_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud.list_inventory(
        db, skip=skip, limit=limit, product_id=product_id, warehouse_id=warehouse_id
    )
    return InventoryListOut(items=items, total=total, skip=skip, limit=limit)


@router.get("/{inventory_id}", response_model=InventoryOut)
async def get_inventory(inventory_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    record = await crud.get_inventory(db, inventory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return record


@router.put("/{inventory_id}", response_model=InventoryOut)
async def update_inventory(inventory_id: uuid.UUID, payload: InventoryUpdate, db: AsyncSession = Depends(get_db)):
    """Overwrite quantity/reorder_threshold to an absolute value (e.g. after a
    physical stock count). For relative changes, use POST /{id}/adjust instead."""
    record = await crud.get_inventory(db, inventory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    return await crud.update_inventory(db, record, payload.model_dump(exclude_unset=True))


@router.post("/{inventory_id}/adjust", response_model=InventoryOut)
async def adjust_inventory(inventory_id: uuid.UUID, payload: InventoryAdjust, db: AsyncSession = Depends(get_db)):
    """Relative stock change (+received shipment / -shipped order), applied
    atomically at the DB level so concurrent adjustments don't overwrite
    each other. Returns 409 if it would push quantity below zero."""
    record = await crud.get_inventory(db, inventory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")

    try:
        updated = await crud.adjust_inventory_quantity(db, inventory_id, payload.delta)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Adjustment of {payload.delta} would take quantity below zero",
        )
    return updated


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory(inventory_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    record = await crud.get_inventory(db, inventory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory record not found")
    await crud.delete_inventory(db, record)
