from __future__ import annotations
from decimal import Decimal
from .transform import invert_check
from .units import parse_unit, needs_transform

def math_ok(x_eur, x_au, gold, unit: str) -> tuple[bool, str]:
    dim = parse_unit(unit)
    if not needs_transform(dim):
        return True, "non-monetary"
    ok = invert_check(x_eur, x_au, gold, dim)
    return ok, "invert" if ok else "invert_fail"

def gold_present(price) -> tuple[bool, str]:
    try:
        p = Decimal(str(price))
    except Exception:
        return False, "gold_unparseable"
    if p <= 0:
        return False, "gold_nonpositive"
    return True, "gold_ok"
