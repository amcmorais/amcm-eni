"""Dimensional unit engine. Do not convert by substring 'EUR' alone."""
from __future__ import annotations
from dataclasses import dataclass

MONETARY = "EUR"
AU = "EUR_AU"  # €Au dimension token in code; display €Au

UNCHANGED_DIMS = frozenset({
    "1", "RATIO", "PERCENT", "INDEX", "PURE",
    "PERSON", "HEAD", "HOUR", "KG", "T", "TONNE",
    "M2", "M3", "TJ", "KWH", "HA",
})


@dataclass(frozen=True)
class Dim:
    """Signed monetary exponent plus a remainder label for non-monetary factors."""
    eur_exp: int  # +1 EUR in numerator, -1 in denominator, 0 none
    scale: str = "1"  # 1 | million | billion | thousand
    rest: str = ""     # /person /hour /kg ...


def parse_unit(unit: str) -> Dim:
    u = (unit or "").strip()
    raw = u
    u_up = u.upper().replace("€", "EUR").replace("EURO", "EUR")
    u_up = u_up.replace("MILLION EUR", "MILLION_EUR").replace("MIO EUR", "MILLION_EUR")
    u_up = u_up.replace("EUR MILLION", "MILLION_EUR").replace("CP_MEUR", "MILLION_EUR")
    u_up = u_up.replace("MEUR", "MILLION_EUR").replace("MIO_EUR", "MILLION_EUR")
    scale = "1"
    if "MILLION_EUR" in u_up or u_up in {"CP_MEUR", "MIO_EUR"}:
        scale = "million"
        u_up = u_up.replace("MILLION_EUR", "EUR")
    if "BILLION_EUR" in u_up:
        scale = "billion"
        u_up = u_up.replace("BILLION_EUR", "EUR")
    if "THOUSAND_EUR" in u_up:
        scale = "thousand"
        u_up = u_up.replace("THOUSAND_EUR", "EUR")

    # ratios / percent / index — no monetary transform
    compact = u_up.replace(" ", "")
    if compact in {"%", "PCT", "PERCENT", "PP"} or "PERCENT" in u_up:
        return Dim(0, "1", "%")
    if "INDEX" in u_up or compact in {"2015=100", "2010=100", "2005=100"}:
        return Dim(0, "1", "index")
    if compact in {"RATIO", "1", "PURE"}:
        return Dim(0, "1", "ratio")

    # kg/EUR or 1/EUR
    if compact.startswith("KG/EUR") or compact.endswith("/EUR") and not compact.startswith("EUR"):
        rest = compact.replace("/EUR", "").replace("EUR", "")
        return Dim(-1, scale, rest or "1")

    if "EUR/EUR" in compact:
        return Dim(0, "1", "EUR/EUR")

    if "EUR" in u_up:
        rest = compact.replace("EUR", "").strip("/")
        return Dim(1, scale, rest)
    return Dim(0, "1", raw)


def output_unit(dim: Dim) -> str:
    if dim.eur_exp == 0:
        return dim.rest or "1"
    scale = {"1": "", "million": "million ", "billion": "billion ", "thousand": "thousand "}.get(dim.scale, "")
    if dim.eur_exp > 0:
        base = f"{scale}€Au".strip()
        return f"{base}/{dim.rest}" if dim.rest else base
    # inverse
    rest = dim.rest or "1"
    return f"{rest}/€Au"


def needs_transform(dim: Dim) -> bool:
    return dim.eur_exp != 0
