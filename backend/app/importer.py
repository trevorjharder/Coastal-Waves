from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import pandas as pd

from . import models, serials


EXPECTED_COLUMNS = {
    "foreign_key",
    "item_desc",
    "location",
    "stocked",
    "sold",
    "quantity",
}


@dataclass
class ImportRow:
    row_number: int
    serial_number: str
    item_desc: str
    painting_code: Optional[str]
    variant_code: Optional[str]
    location_code: Optional[str]
    stocked: int
    sold: int
    quantity: int
    errors: List[str]


@dataclass
class ImportResult:
    dry_run: bool
    imported: int
    failed: int
    rows: List[ImportRow]


def _normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


def _normalize_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_dataframe(upload) -> pd.DataFrame:
    try:
        df = pd.read_excel(upload, sheet_name="Inventory")
    except ValueError as exc:
        raise ValueError("Worksheet 'Inventory' not found in workbook") from exc
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
    return df


def _validate_columns(columns: Iterable[str]) -> List[str]:
    missing = [col for col in EXPECTED_COLUMNS if col not in columns]
    return missing


def process_inventory_upload(upload, db, dry_run: bool) -> ImportResult:
    df = _load_dataframe(upload)
    missing = _validate_columns(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    rows: List[ImportRow] = []
    imported = 0
    failed = 0

    for idx, row in df.iterrows():
        errors: List[str] = []
        serial_raw = str(row.get("foreign_key", "")).strip()
        item_desc = str(row.get("item_desc", "")).strip()
        painting_code: Optional[str] = None
        variant_code: Optional[str] = None
        location_code: Optional[str] = None
        stocked = _normalize_int(row.get("stocked"))
        sold = _normalize_int(row.get("sold"))
        quantity = _normalize_int(row.get("quantity"))
        if quantity == 0 and (stocked or sold):
            quantity = max(stocked - sold, 0)

        provided_location_code = str(row.get("location", "")).strip().upper()

        if not serial_raw:
            errors.append("Serial number is required")
        else:
            try:
                components = serials.parse_serial_number(serial_raw)
                painting_code = components.painting_code
                variant_code = components.variant_code
                location_code = components.location_code
            except ValueError as exc:
                errors.append(str(exc))

        if location_code and provided_location_code and location_code != provided_location_code:
            errors.append("Location column does not match serial number")
        elif not location_code and provided_location_code:
            location_code = provided_location_code

        painting = None
        if painting_code:
            painting = db.query(models.Painting).filter_by(code=painting_code).first()
            if not painting:
                errors.append(f"Painting code '{painting_code}' not found")

        variant = None
        if painting and variant_code:
            for candidate in painting.variants:
                short_code = serials.build_variant_code(
                    candidate.category,
                    candidate.size,
                    candidate.stretch,
                    candidate.framing,
                )
                if short_code == variant_code:
                    variant = candidate
                    break
            if not variant:
                errors.append(
                    f"Variant code '{variant_code}' not mapped to painting '{painting_code}'"
                )

        location = None
        if location_code:
            location = db.query(models.Location).filter_by(code=location_code).first()
            if not location:
                errors.append(f"Location code '{location_code}' not found")

        inventory_serial = serial_raw
        if painting and variant and location and not errors:
            expected_components = serials.SerialComponents(
                painting_code=painting.code.upper(),
                variant_code=serials.build_variant_code(
                    variant.category, variant.size, variant.stretch, variant.framing
                ),
                location_code=location.code.upper(),
                sequence=serials.parse_serial_number(serial_raw).sequence,
            )
            try:
                serials.validate_serial_against_components(serial_raw, expected_components)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                parsed = serials.parse_serial_number(serial_raw)
                existing_count = (
                    db.query(models.InventoryItem)
                    .filter(models.InventoryItem.serial_number.like(f"PTG-{painting.code.upper()}-%"))
                    .count()
                )
                if parsed.sequence == "0000":
                    sequence = serials.next_sequence_number(existing_count)
                    inventory_serial = expected_components.serial_number.replace(
                        parsed.sequence, sequence
                    )

                duplicate = (
                    db.query(models.InventoryItem)
                    .filter_by(serial_number=inventory_serial)
                    .first()
                )
                if duplicate:
                    errors.append("Serial number already exists in inventory")

        import_row = ImportRow(
            row_number=idx + 2,  # account for header row in spreadsheets
            serial_number=inventory_serial,
            item_desc=item_desc,
            painting_code=painting_code,
            variant_code=variant_code,
            location_code=location_code,
            stocked=stocked,
            sold=sold,
            quantity=quantity,
            errors=errors,
        )
        rows.append(import_row)

        if not errors and painting and variant and location:
            if dry_run:
                imported += 1
            else:
                record = models.InventoryItem(
                    painting_id=painting.id,
                    variant_id=variant.id,
                    location_id=location.id,
                    serial_number=inventory_serial,
                    quantity=quantity,
                    unit_cost=0.0,
                    unit_price=0.0,
                )
                db.add(record)
                imported += 1
        elif errors:
            failed += 1

    if not dry_run:
        db.commit()

    return ImportResult(
        dry_run=dry_run,
        imported=imported,
        failed=failed,
        rows=rows,
    )
