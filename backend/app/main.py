from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas, serials
from .database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Coastal Waves Inventory API")


@app.get("/health")
def health():
    return {"status": "ok"}


# Painting endpoints
@app.post("/paintings", response_model=schemas.PaintingRead)
def create_painting(painting: schemas.PaintingCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Painting).filter_by(code=painting.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Painting code already exists")
    record = models.Painting(**painting.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/paintings", response_model=List[schemas.PaintingRead])
def list_paintings(db: Session = Depends(get_db)):
    return db.query(models.Painting).all()


@app.get("/paintings/{painting_id}", response_model=schemas.PaintingRead)
def get_painting(painting_id: int, db: Session = Depends(get_db)):
    record = db.query(models.Painting).get(painting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Painting not found")
    return record


@app.delete("/paintings/{painting_id}")
def delete_painting(painting_id: int, db: Session = Depends(get_db)):
    record = db.query(models.Painting).get(painting_id)
    if not record:
        raise HTTPException(status_code=404, detail="Painting not found")
    db.delete(record)
    db.commit()
    return {"status": "deleted"}


# Variant endpoints
@app.post("/variants", response_model=schemas.VariantRead)
def create_variant(variant: schemas.VariantCreate, db: Session = Depends(get_db)):
    painting = db.query(models.Painting).get(variant.painting_id)
    if not painting:
        raise HTTPException(status_code=404, detail="Painting not found")
    existing = (
        db.query(models.ProductVariant)
        .filter_by(
            painting_id=variant.painting_id,
            category=variant.category,
            size=variant.size,
            stretch=variant.stretch,
            framing=variant.framing,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Variant already exists for painting")
    record = models.ProductVariant(**variant.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    short_code = serials.build_variant_code(record.category, record.size, record.stretch, record.framing)
    return schemas.VariantRead(short_code=short_code, **record.__dict__)


@app.get("/variants", response_model=List[schemas.VariantRead])
def list_variants(db: Session = Depends(get_db)):
    variants = db.query(models.ProductVariant).all()
    result = []
    for variant in variants:
        short_code = serials.build_variant_code(variant.category, variant.size, variant.stretch, variant.framing)
        result.append(schemas.VariantRead(short_code=short_code, **variant.__dict__))
    return result


# Location endpoints
@app.post("/locations", response_model=schemas.LocationRead)
def create_location(location: schemas.LocationCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Location).filter(
        (models.Location.name == location.name) | (models.Location.code == location.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location name or code already exists")
    record = models.Location(**location.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/locations", response_model=List[schemas.LocationRead])
def list_locations(db: Session = Depends(get_db)):
    return db.query(models.Location).all()


# Inventory endpoints
@app.post("/inventory", response_model=schemas.InventoryRead)
def create_inventory_item(item: schemas.InventoryCreate, db: Session = Depends(get_db)):
    painting = db.query(models.Painting).get(item.painting_id)
    variant = db.query(models.ProductVariant).get(item.variant_id)
    location = db.query(models.Location).get(item.location_id)
    if not painting or not variant or not location:
        raise HTTPException(status_code=400, detail="Painting, variant, or location not found")

    expected_serial = serials.SerialComponents(
        painting_code=painting.code.upper(),
        variant_code=serials.build_variant_code(variant.category, variant.size, variant.stretch, variant.framing),
        location_code=location.code.upper(),
        sequence=serials.parse_serial_number(item.serial_number).sequence,
    )
    try:
        serials.validate_serial_against_components(item.serial_number, expected_serial)
    except ValueError as exc:  # pragma: no cover - FastAPI handles
        raise HTTPException(status_code=400, detail=str(exc))

    existing_count = (
        db.query(models.InventoryItem)
        .filter(models.InventoryItem.serial_number.like(f"PTG-{painting.code.upper()}-%"))
        .count()
    )
    parsed = serials.parse_serial_number(item.serial_number)
    if parsed.sequence == "0000":
        sequence = serials.next_sequence_number(existing_count)
        item.serial_number = expected_serial.serial_number.replace(parsed.sequence, sequence)

    record = models.InventoryItem(**item.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/inventory", response_model=List[schemas.InventoryRead])
def list_inventory(db: Session = Depends(get_db)):
    return db.query(models.InventoryItem).all()


# Transaction endpoints
@app.post("/transactions", response_model=schemas.TransactionRead)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    item = db.query(models.InventoryItem).get(transaction.inventory_item_id)
    location = db.query(models.Location).get(transaction.location_id)
    if not item or not location:
        raise HTTPException(status_code=400, detail="Inventory item or location not found")

    record = models.Transaction(**transaction.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/transactions", response_model=List[schemas.TransactionRead])
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()


# Aggregate endpoints
@app.get("/reports/stock", response_model=List[schemas.LocationStockSummary])
def stock_by_location(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Location.id.label("location_id"),
            models.Location.name.label("location_name"),
            models.Location.is_home,
            func.sum(models.InventoryItem.quantity).label("on_hand"),
        )
        .join(models.InventoryItem, models.Location.id == models.InventoryItem.location_id)
        .group_by(models.Location.id)
        .all()
    )
    return [schemas.LocationStockSummary(**row._asdict()) for row in rows]


@app.get("/reports/sales", response_model=List[schemas.LocationSalesSummary])
def sales_by_location(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Location.id.label("location_id"),
            models.Location.name.label("location_name"),
            models.Location.is_home,
            func.sum(models.Transaction.quantity).label("sold"),
            func.sum(models.Transaction.total_price).label("revenue"),
        )
        .join(models.Location, models.Transaction.location_id == models.Location.id)
        .filter(models.Transaction.type == "sale")
        .group_by(models.Location.id)
        .all()
    )
    return [schemas.LocationSalesSummary(**row._asdict()) for row in rows]


@app.get("/reports/home", response_model=dict)
def home_grouping(db: Session = Depends(get_db)):
    home_locations = db.query(models.Location).filter(models.Location.is_home.is_(True)).all()
    home_ids = [loc.id for loc in home_locations]
    on_hand = (
        db.query(func.sum(models.InventoryItem.quantity))
        .filter(models.InventoryItem.location_id.in_(home_ids))
        .scalar()
        or 0
    )
    sold = (
        db.query(func.sum(models.Transaction.quantity))
        .filter(models.Transaction.location_id.in_(home_ids), models.Transaction.type == "sale")
        .scalar()
        or 0
    )
    revenue = (
        db.query(func.sum(models.Transaction.total_price))
        .filter(models.Transaction.location_id.in_(home_ids), models.Transaction.type == "sale")
        .scalar()
        or 0.0
    )
    return {"on_hand": int(on_hand), "sold": int(sold), "revenue": float(revenue)}
