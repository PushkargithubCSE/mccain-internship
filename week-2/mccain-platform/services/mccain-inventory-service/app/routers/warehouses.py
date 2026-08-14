import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    InventoryWithProductOut,
    WarehouseCreate,
    WarehouseListOut,
    WarehouseOut,
    WarehouseUpdate,
)

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.post("", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
async def create_warehouse(payload: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await crud.create_warehouse(db, **payload.model_dump())
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Warehouse code '{payload.code}' already exists")


@router.get("", response_model=WarehouseListOut)
async def list_warehouses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud.list_warehouses(db, skip=skip, limit=limit)
    return WarehouseListOut(items=items, total=total, skip=skip, limit=limit)


@router.get("/{warehouse_id}", response_model=WarehouseOut)
async def get_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    warehouse = await crud.get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseOut)
async def update_warehouse(warehouse_id: uuid.UUID, payload: WarehouseUpdate, db: AsyncSession = Depends(get_db)):
    warehouse = await crud.get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return await crud.update_warehouse(db, warehouse, payload.model_dump(exclude_unset=True))


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    warehouse = await crud.get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    await crud.delete_warehouse(db, warehouse)  # cascades: also removes its inventory rows


@router.get("/{warehouse_id}/inventory", response_model=list[InventoryWithProductOut])
async def get_warehouse_inventory(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Every product currently stocked in this warehouse, with quantities."""
    warehouse = await crud.get_warehouse(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return await crud.list_inventory_by_warehouse(db, warehouse_id)
