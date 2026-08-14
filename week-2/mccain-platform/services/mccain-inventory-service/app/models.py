"""
Schema design
-------------
Product <--1---M--> Inventory <--M---1--> Warehouse

A product can be stocked in many warehouses, and a warehouse holds many
products, in different quantities — a classic many-to-many. But since we
need an attribute on the relationship itself (quantity), a plain
`secondary=` join table isn't enough; we model `Inventory` as its own
entity (the "association object" pattern) with a foreign key to each side
plus its own columns.

`UniqueConstraint(product_id, warehouse_id)` guarantees one stock row per
product per warehouse — the DB enforces "no duplicate stock records"
rather than relying on application code to check first.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One product -> many inventory rows (one per warehouse it's stocked in).
    # cascade="all, delete-orphan": deleting a product deletes its stock
    # records too — there's no such thing as inventory for a product that
    # no longer exists.
    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product {self.sku} ({self.name})>"


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    inventory_records: Mapped[list["Inventory"]] = relationship(
        back_populates="warehouse", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Warehouse {self.code} ({self.name})>"


class Inventory(Base):
    """The association object: how much of a given product sits in a given
    warehouse. This is the table that actually makes Product<->Warehouse
    a many-to-many relationship."""

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_product_warehouse"),
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    reorder_threshold: Mapped[int] = mapped_column(nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship(back_populates="inventory_records")
    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} warehouse={self.warehouse_id} qty={self.quantity}>"
