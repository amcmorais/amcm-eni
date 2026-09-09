from decimal import Decimal
from aurum.units import parse_unit, output_unit, needs_transform
from aurum.transform import transform_value, invert_check, factor, equity_au_return
from aurum.definition import AU_PER_TROY_OZ


def test_definition_fixed():
    assert AU_PER_TROY_OZ == Decimal("100")


def test_million_eur_to_million_au():
    dim = parse_unit("million EUR")
    assert dim.eur_exp == 1 and dim.scale == "million"
    # X=16200000 million EUR, gold=3776 → au = 16200000 * 100 / 3776
    au = transform_value(16200000, 3776, dim)
    assert invert_check(16200000, au, 3776, dim)
    assert "€Au" in output_unit(dim)


def test_percent_unchanged():
    dim = parse_unit("%")
    assert not needs_transform(dim)
    assert transform_value(2.4, 3776, dim) == Decimal("2.4")


def test_kg_per_eur_inverse():
    dim = parse_unit("kg/EUR")
    assert dim.eur_exp == -1
    au = transform_value(Decimal("2"), 200, dim)
    # f=100/200=0.5; inverse x/f = 4
    assert au == Decimal("4")


def test_equity_return_uses_both_golds():
    # EUR flat 100→100, gold 100→200 → €Au halves
    r = equity_au_return(100, 200, 100, 100)
    assert r == Decimal("-0.5")


def test_factor():
    assert factor(200) == Decimal("0.5")
