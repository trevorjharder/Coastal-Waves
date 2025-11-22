from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class Painting(Base):
    __tablename__ = "paintings"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    variants = relationship("ProductVariant", back_populates="painting", cascade="all, delete-orphan")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("painting_id", "category", "size", "stretch", "framing", name="uix_variant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    painting_id = Column(Integer, ForeignKey("paintings.id"), nullable=False)
    category = Column(String(50), nullable=False)
    size = Column(String(50), nullable=False)
    stretch = Column(Boolean, default=False, nullable=False)
    framing = Column(Boolean, default=False, nullable=False)

    painting = relationship("Painting", back_populates="variants")
    inventory_items = relationship("InventoryItem", back_populates="variant")


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_home = Column(Boolean, default=False, nullable=False)
    code = Column(String(12), unique=True, nullable=False)

    inventory_items = relationship("InventoryItem", back_populates="location")
    transactions = relationship("Transaction", back_populates="location")


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("serial_number", name="uix_serial_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    painting_id = Column(Integer, ForeignKey("paintings.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    serial_number = Column(String(255), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Float, default=0.0, nullable=False)
    unit_price = Column(Float, default=0.0, nullable=False)

    painting = relationship("Painting")
    variant = relationship("ProductVariant", back_populates="inventory_items")
    location = relationship("Location", back_populates="inventory_items")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    type = Column(String(20), nullable=False)  # sale or transfer
    quantity = Column(Integer, default=1, nullable=False)
    total_price = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    inventory_item = relationship("InventoryItem")
    location = relationship("Location", back_populates="transactions")
