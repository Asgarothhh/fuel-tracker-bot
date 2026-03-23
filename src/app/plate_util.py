"""Нормализация госномеров для сопоставления со справочником автомобилей."""

import re


def normalize_plate(text: str) -> str:
    if not text:
        return ""
    t = text.strip().upper()
    t = re.sub(r"[\s\-\.\t\n\r]+", "", t)
    return t


def plates_equal(a: str, b: str) -> bool:
    return normalize_plate(a) == normalize_plate(b)


def find_cars_by_normalized_plate(db, norm: str):
    """Все автомобили из БД, у которых госномер совпадает с нормализованным вводом."""
    from src.app.models import Car

    n = normalize_plate(norm)
    if not n:
        return []
    return [c for c in db.query(Car).all() if normalize_plate(c.plate) == n]
