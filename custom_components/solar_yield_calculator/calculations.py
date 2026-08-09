"""Pure calculation helpers for Solar Yield Calculator."""

from __future__ import annotations


def gross_grid_price_eur_kwh(
    energy_price_net_ct: float,
    network_fee_net_ct: float,
    taxes_net_ct: float,
    vat_percent: float,
) -> float:
    """Return gross avoided grid price in EUR/kWh."""
    net_ct = energy_price_net_ct + network_fee_net_ct + taxes_net_ct
    gross_ct = net_ct * (1.0 + vat_percent / 100.0)
    return gross_ct / 100.0


def normalize_epex_price_eur_kwh(value: float, unit: str) -> float:
    """Normalize an EPEX price to EUR/kWh."""
    if unit == "EUR/kWh":
        return value
    if unit == "ct/kWh":
        return value / 100.0
    if unit == "EUR/MWh":
        return value / 1000.0
    raise ValueError(f"Unsupported EPEX unit: {unit}")


def effective_epex_price_eur_kwh(
    value: float,
    unit: str,
    adjustment_ct_kwh: float,
) -> float:
    """Return effective EPEX remuneration after an adjustment."""
    return normalize_epex_price_eur_kwh(value, unit) + adjustment_ct_kwh / 100.0


def self_supply_power_kw(
    house_load_kw: float,
    grid_import_kw: float,
    grid_to_battery_power_kw: float = 0.0,
) -> float:
    """Return house load supplied by PV/battery instead of the grid.

    Grid import used to charge the battery is removed from the grid import
    attributed to the house. The result is clamped to the actual house load.
    """
    grid_for_house_kw = max(grid_import_kw - max(grid_to_battery_power_kw, 0.0), 0.0)
    return min(max(house_load_kw - grid_for_house_kw, 0.0), max(house_load_kw, 0.0))


def self_supply_energy_kwh(
    house_energy_kwh: float,
    grid_import_energy_kwh: float,
    grid_to_battery_energy_kwh: float,
) -> float:
    """Return interval house energy supplied by PV/battery.

    This is the energy-domain equivalent of ``self_supply_power_kw`` and is
    preferred for settlement periods because grid-to-battery is measured as
    an energy counter by many inverters.
    """
    grid_for_house_kwh = max(
        grid_import_energy_kwh - max(grid_to_battery_energy_kwh, 0.0), 0.0
    )
    return min(
        max(house_energy_kwh - grid_for_house_kwh, 0.0),
        max(house_energy_kwh, 0.0),
    )


def export_revenue_rate_eur_h(export_power_kw: float, epex_eur_kwh: float) -> float:
    """Return instantaneous export revenue rate in EUR/h."""
    return max(export_power_kw, 0.0) * epex_eur_kwh


def self_consumption_saving_rate_eur_h(
    self_supply_kw: float,
    gross_grid_price_eur_kwh_value: float,
) -> float:
    """Return instantaneous avoided grid cost rate in EUR/h."""
    return max(self_supply_kw, 0.0) * gross_grid_price_eur_kwh_value
