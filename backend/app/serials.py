from __future__ import annotations

import re
from dataclasses import dataclass

SERIAL_PATTERN = re.compile(
    r"^PTG-(?P<painting>[A-Z0-9]{2,10})-"  # painting code
    r"(?P<variant>[A-Z0-9]{2,12})-"  # variant short code
    r"(?P<location>[A-Z0-9]{2,8})-"  # location code
    r"(?P<sequence>\d{4})$"
)


@dataclass
class SerialComponents:
    painting_code: str
    variant_code: str
    location_code: str
    sequence: str

    @property
    def serial_number(self) -> str:
        return f"PTG-{self.painting_code}-{self.variant_code}-{self.location_code}-{self.sequence}"


def parse_serial_number(serial_number: str) -> SerialComponents:
    match = SERIAL_PATTERN.match(serial_number.strip())
    if not match:
        raise ValueError(
            "Serial number must follow PTG-<PAINTING>-<VARIANT>-<LOCATION>-<SEQUENCE> with codes in uppercase."
        )
    return SerialComponents(
        painting_code=match.group("painting"),
        variant_code=match.group("variant"),
        location_code=match.group("location"),
        sequence=match.group("sequence"),
    )


def build_variant_code(category: str, size: str, stretch: bool, framing: bool) -> str:
    category_part = re.sub(r"[^A-Z0-9]", "", category.upper())[:4]
    size_part = re.sub(r"[^A-Z0-9]", "", size.upper())[:4]
    stretch_part = "S" if stretch else "N"
    frame_part = "F" if framing else "N"
    code = f"{category_part}{size_part}{stretch_part}{frame_part}"
    return code


def validate_serial_against_components(serial_number: str, expected: SerialComponents) -> None:
    parsed = parse_serial_number(serial_number)
    if parsed.painting_code != expected.painting_code:
        raise ValueError("Painting code in serial number does not match record.")
    if parsed.variant_code != expected.variant_code:
        raise ValueError("Variant code in serial number does not match record.")
    if parsed.location_code != expected.location_code:
        raise ValueError("Location code in serial number does not match record.")


def next_sequence_number(existing_count: int) -> str:
    return str(existing_count + 1).zfill(4)
