import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ---------- Product ----------


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, decimal_places=2)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---------- Warehouse ----------


class WarehouseBase(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=255)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)


class WarehouseOut(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


# ---------- Inventory ----------


class InventoryCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(ge=0)
    reorder_threshold: int = Field(default=0, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    reorder_threshold: int | None = Field(default=None, ge=0)


class InventoryAdjust(BaseModel):
    """Relative change to stock, e.g. -5 to ship out 5 units, +100 to receive a shipment."""

    delta: int = Field(description="Positive to add stock, negative to remove it")


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reorder_threshold: int
    updated_at: datetime


class InventoryWithProductOut(InventoryOut):
    """Used by GET /warehouses/{id}/inventory — includes product details inline."""

    product: ProductOut


class InventoryWithWarehouseOut(InventoryOut):
    """Used by GET /products/{id}/inventory — includes warehouse details inline."""

    warehouse: WarehouseOut


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    skip: int
    limit: int


class WarehouseListOut(BaseModel):
    items: list[WarehouseOut]
    total: int
    skip: int
    limit: int


class InventoryListOut(BaseModel):
    items: list[InventoryOut]
    total: int
    skip: int
    limit: int
