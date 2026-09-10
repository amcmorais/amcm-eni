
"""Long scale for published €Au magnitudes.

million  = 10^6
milliard = 10^9
billion  = 10^12 = M^2
trillion = 10^18 = M^3

The short-scale use of "billion" for 10^9 is not used.
"""
from __future__ import annotations

SCALE = (
    (1e18, "trillion", "M3"),
    (1e12, "billion", "M2"),
    (1e9, "milliard", "10^9"),
    (1e6, "million", "10^6"),
)

RULE = (
    "Magnitudes follow the long scale: million = 10^6; milliard = 10^9; "
    "billion = 10^12 = M^2; trillion = 10^18 = M^3. "
    "The short-scale assignment of billion to 10^9 is not used."
)


def split(value: float) -> tuple[float, str, str]:
    x = abs(float(value))
    sign = -1 if value < 0 else 1
    for thresh, name, code in SCALE:
        if x >= thresh:
            return (sign * x / thresh, name, code)
    return (float(value), "", "")


def format_au(value, places: int = 4) -> str:
    if value is None:
        return "—"
    coeff, name, _ = split(float(value))
    body = f"{coeff:,.{places}f}"
    if name:
        return f"{body} {name} €Au"
    return f"{body} €Au"
