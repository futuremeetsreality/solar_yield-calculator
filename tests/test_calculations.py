"""Tests for Solar Yield Calculator calculation helpers."""

from custom_components.solar_yield_calculator.calculations import (
    effective_epex_price_eur_kwh,
    gross_grid_price_eur_kwh,
    self_supply_energy_kwh,
    self_supply_power_kw,
)


def test_gross_grid_price() -> None:
    assert gross_grid_price_eur_kwh(15, 10, 4, 20) == 0.348


def test_epex_normalization_and_adjustment() -> None:
    assert effective_epex_price_eur_kwh(18.441, "ct/kWh", 0) == 0.18441
    assert effective_epex_price_eur_kwh(184.41, "EUR/MWh", -0.5) == 0.17941


def test_self_supply_power_without_grid_battery() -> None:
    assert self_supply_power_kw(2.0, 0.5) == 1.5


def test_self_supply_power_corrects_grid_battery_power() -> None:
    assert self_supply_power_kw(1.0, 2.5, 2.0) == 0.5
    assert self_supply_power_kw(1.0, 3.0, 3.0) == 1.0


def test_self_supply_energy_corrects_grid_battery_energy() -> None:
    assert self_supply_energy_kwh(1.0, 2.0, 2.0) == 1.0
    assert self_supply_energy_kwh(1.0, 1.5, 0.5) == 0.0
    assert self_supply_energy_kwh(1.0, 0.25, 0.0) == 0.75
