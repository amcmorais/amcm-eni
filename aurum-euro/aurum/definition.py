"""Immutable metrological definition. Never varies with the gold market price."""
from decimal import Decimal

AU_DEFINITION_VERSION = "1.0.0-philharmoniker"
TRANSFORMATION_VERSION = "1.0.0"
TRANSFORMATION_FORMULA = "X_au = X_eur * (100 / P_au_eur)"

# 100 €Au = 1 troy oz Au 999.9
AU_PER_TROY_OZ = Decimal("100")
TROY_OZ_PER_AU = Decimal("0.01")
GRAMS_PER_TROY_OZ = Decimal("31.1034768")
GRAMS_PER_AU = GRAMS_PER_TROY_OZ * TROY_OZ_PER_AU  # 0.311034768
PURITY = "Au999.9"
REFERENCE_INSTRUMENT = "Wiener Philharmoniker 1 troy oz Au 999.9 (Austrian Mint)"
FACIAL_DENOMINATION_NOTE = "100 EURO facial on the 1 oz coin is the €Au count, not a fiat peg"

DEFINITION = {
    "id": "eur-au",
    "symbol": "€Au",
    "version": AU_DEFINITION_VERSION,
    "equation": "100 €Au = 1 troy oz Au 999.9",
    "one_au_troy_oz": str(TROY_OZ_PER_AU),
    "one_au_grams": str(GRAMS_PER_AU),
    "purity": PURITY,
    "reference_instrument": REFERENCE_INSTRUMENT,
    "facial_note": FACIAL_DENOMINATION_NOTE,
    "formula": TRANSFORMATION_FORMULA,
    "transformation_version": TRANSFORMATION_VERSION,
    "not": [
        "€Au is not redefined by the current EUR gold price",
        "the engine does not assert real growth, inflation, or welfare",
    ],
}
