from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaintingBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=10)
    name: str


class PaintingCreate(PaintingBase):
    pass


class PaintingRead(PaintingBase):
    id: int

    class Config:
        from_attributes = True


class VariantBase(BaseModel):
    painting_id: int
    category: str
    size: str
    stretch: bool = False
    framing: bool = False


class VariantCreate(VariantBase):
    pass


class VariantRead(VariantBase):
    id: int
    short_code: str

    class Config:
        from_attributes = True


class LocationBase(BaseModel):
    name: str
    code: str
    is_home: bool = False


class LocationCreate(LocationBase):
    pass


class LocationRead(LocationBase):
    id: int

    class Config:
        from_attributes = True


class InventoryBase(BaseModel):
    painting_id: int
    variant_id: int
    location_id: int
    serial_number: str
    quantity: int = 0
    unit_cost: float = 0.0
    unit_price: float = 0.0


class InventoryCreate(InventoryBase):
    pass


class InventoryRead(InventoryBase):
    id: int

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    inventory_item_id: int
    location_id: int
    type: str
    quantity: int = 1
    total_price: float = 0.0


class TransactionCreate(TransactionBase):
    pass


class TransactionRead(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LocationStockSummary(BaseModel):
    location_id: int
    location_name: str
    is_home: bool
    on_hand: int


class LocationSalesSummary(BaseModel):
    location_id: int
    location_name: str
    is_home: bool
    sold: int
    revenue: float
