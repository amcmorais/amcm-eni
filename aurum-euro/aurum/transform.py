"""Deterministic €Au transform. Same inputs → same output."""
from __future__ import annotations
from decimal import Decimal, getcontext
from .definition import AU_PER_TROY_OZ, AU_DEFINITION_VERSION, TRANSFORMATION_VERSION, TRANSFORMATION_FORMULA
from .units import Dim, needs_transform, output_unit

getcontext().prec = 28


def factor(gold_eur_per_troy_oz: Decimal | float | str) -> Decimal:
    p = Decimal(str(gold_eur_per_troy_oz))
    if p <= 0:
        raise ValueError("gold price must be positive")
    return AU_PER_TROY_OZ / p


def transform_value(x_eur, gold_eur_per_troy_oz, dim: Dim) -> Decimal:
    x = Decimal(str(x_eur))
    f = factor(gold_eur_per_troy_oz)
    if not needs_transform(dim):
        return x
    if dim.eur_exp > 0:
        return x * f
    return x / f  # EUR in denominator


def invert_check(x_eur, x_au, gold_eur_per_troy_oz, dim: Dim, tol=Decimal("1e-8")) -> bool:
    if not needs_transform(dim):
        return Decimal(str(x_eur)) == Decimal(str(x_au))
    p = Decimal(str(gold_eur_per_troy_oz))
    if dim.eur_exp > 0:
        recon = Decimal(str(x_au)) * p / AU_PER_TROY_OZ
    else:
        recon = Decimal(str(x_au)) * AU_PER_TROY_OZ / p
    return abs(recon - Decimal(str(x_eur))) <= tol * max(Decimal("1"), abs(Decimal(str(x_eur))))


def provenance(*, source, dataset, dataset_version, entity, indicator, reference_period, frequency,
               original_value, original_unit, gold_source, gold_observation_date_or_period,
               gold_price, gold_alignment_method, derived_value, derived_unit,
               retrieved_at, generated_at) -> dict:
    return {
        "source": source,
        "dataset": dataset,
        "dataset_version": dataset_version,
        "entity": entity,
        "indicator": indicator,
        "reference_period": reference_period,
        "frequency": frequency,
        "original_value": str(original_value),
        "original_unit": original_unit,
        "gold_source": gold_source,
        "gold_observation_date_or_period": gold_observation_date_or_period,
        "gold_price": str(gold_price),
        "gold_unit": "EUR/troy oz Au 999.9",
        "gold_alignment_method": gold_alignment_method,
        "au_definition_version": AU_DEFINITION_VERSION,
        "transformation_formula": TRANSFORMATION_FORMULA,
        "transformation_version": TRANSFORMATION_VERSION,
        "derived_value": str(derived_value),
        "derived_unit": derived_unit,
        "retrieved_at": retrieved_at,
        "generated_at": generated_at,
    }


def equity_au_return(p_eur_t1, gold_t1, p_eur_t0, gold_t0) -> Decimal:
    """Period return from the €Au series, not EUR return × current gold factor."""
    a1 = Decimal(str(p_eur_t1)) * factor(gold_t1)
    a0 = Decimal(str(p_eur_t0)) * factor(gold_t0)
    if a0 == 0:
        raise ValueError("zero base price")
    return a1 / a0 - 1


ALIGNMENT = {
    "D": "observation_date",
    "M": "monthly_average",
    "Q": "quarterly_average",
    "A": "annual_average",
    "stock": "period_end",
    "flow-M": "monthly_average",
    "flow-Q": "quarterly_average",
    "flow-A": "annual_average",
}
