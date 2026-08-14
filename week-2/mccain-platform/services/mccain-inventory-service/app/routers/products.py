import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    InventoryWithWarehouseOut,
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await crud.create_product(db, **payload.model_dump())
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"SKU '{payload.sku}' already exists")


@router.get("", response_model=ProductListOut)
async def list_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    name: str | None = Query(default=None, description="Case-insensitive substring match on product name"),
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud.list_products(db, skip=skip, limit=limit, name_contains=name)
    return ProductListOut(items=items, total=total, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(product_id: uuid.UUID, payload: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return await crud.update_product(db, product, payload.model_dump(exclude_unset=True))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    await crud.delete_product(db, product)  # cascades: also removes its inventory rows


@router.get("/{product_id}/inventory", response_model=list[InventoryWithWarehouseOut])
async def get_product_inventory(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Stock levels for this product across every warehouse that carries it."""
    product = await crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return await crud.list_inventory_by_product(db, product_id)
