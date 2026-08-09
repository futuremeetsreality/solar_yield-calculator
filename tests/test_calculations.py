"""Tests for calculation helpers."""

from custom_components.solar_yield_calculator.calculations import (
    effective_epex_price_eur_kwh,
    export_revenue_rate_eur_h,
    gross_grid_price_eur_kwh,
    self_consumption_saving_rate_eur_h,
    self_supply_power_kw,
)


def test_gross_grid_price() -> None:
    assert gross_grid_price_eur_kwh(14.0, 10.0, 4.0, 20.0) == 0.336


def test_epex_normalization_and_adjustment() -> None:
    assert effective_epex_price_eur_kwh(8.0, "ct/kWh", -0.5) == 0.075


def test_self_supply_never_negative() -> None:
    assert self_supply_power_kw(5.0, 0.5) == 4.5
    assert self_supply_power_kw(1.0, 2.0) == 0.0


def test_rates() -> None:
    assert export_revenue_rate_eur_h(6.0, 0.08) == 0.48
    assert self_consumption_saving_rate_eur_h(3.5, 0.336) == 1.176
