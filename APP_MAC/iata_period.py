"""Detecta únicamente las fechas del encabezado; no interpreta importes."""
from datetime import date
import re

MONTHS = {name: number for number, name in enumerate(
    ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'), 1)}

def period_from_text(text):
    match = re.search(
        r'Billing\s+Period\s*:\s*\d{6}\s*\(\s*(\d{2}-[A-Z]{3}-\d{4})\s+to\s+(\d{2}-[A-Z]{3}-\d{4})\s*\)',
        text or '', re.IGNORECASE)
    if not match:
        return None
    try:
        def parse(value):
            day, month, year = value.upper().split('-')
            return date(int(year), MONTHS[month], int(day))
        start, end = parse(match[1]), parse(match[2])
        return (start, end) if start <= end else None
    except (ValueError, KeyError):
        return None
