"""Sensor platform for Solar Yield Calculator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .accounting import SolarYieldAccounting
from .calculations import (
    export_revenue_rate_eur_h,
    self_consumption_saving_rate_eur_h,
    self_supply_power_kw,
)
from .const import DATA_ACCOUNTING, DOMAIN, VERSION


@dataclass(frozen=True, kw_only=True)
class YieldSensorDescription:
    """Description for a calculated sensor."""

    key: str
    native_unit: str
    icon: str
    value_fn: Callable[[SolarYieldAccounting], float | None]
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass = SensorStateClass.MEASUREMENT
    suggested_display_precision: int | None = None
    quarter_total: bool = False
    period: str | None = None


def _live_self_supply(accounting: SolarYieldAccounting) -> float:
    return self_supply_power_kw(
        accounting.live.house_kw,
        accounting.live.grid_import_kw,
    )


def _live_export_rate(accounting: SolarYieldAccounting) -> float:
    return export_revenue_rate_eur_h(
        accounting.live.grid_export_kw,
        accounting.live.epex_eur_kwh,
    )


def _live_saving_rate(accounting: SolarYieldAccounting) -> float:
    return self_consumption_saving_rate_eur_h(
        _live_self_supply(accounting),
        accounting.live.grid_price_eur_kwh,
    )


def _live_total_rate(accounting: SolarYieldAccounting) -> float:
    return _live_export_rate(accounting) + _live_saving_rate(accounting)


def _period_value(period: str, field: str) -> Callable[[SolarYieldAccounting], float]:
    return lambda accounting: float(getattr(accounting.periods[period], field))


SENSORS: tuple[YieldSensorDescription, ...] = (
    YieldSensorDescription(
        key="grid_price_gross",
        native_unit="EUR/kWh",
        icon="mdi:cash",
        value_fn=lambda a: a.live.grid_price_eur_kwh,
        suggested_display_precision=4,
    ),
    YieldSensorDescription(
        key="effective_epex_price",
        native_unit="EUR/kWh",
        icon="mdi:chart-line",
        value_fn=lambda a: a.live.epex_eur_kwh,
        suggested_display_precision=5,
    ),
    YieldSensorDescription(
        key="self_supply_power",
        native_unit=UnitOfPower.KILO_WATT,
        icon="mdi:home-lightning-bolt",
        value_fn=_live_self_supply,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=3,
    ),
    YieldSensorDescription(
        key="export_revenue_rate",
        native_unit="EUR/h",
        icon="mdi:cash-plus",
        value_fn=_live_export_rate,
        suggested_display_precision=4,
    ),
    YieldSensorDescription(
        key="self_consumption_saving_rate",
        native_unit="EUR/h",
        icon="mdi:home-currency-eur",
        value_fn=_live_saving_rate,
        suggested_display_precision=4,
    ),
    YieldSensorDescription(
        key="total_benefit_rate",
        native_unit="EUR/h",
        icon="mdi:cash-check",
        value_fn=_live_total_rate,
        suggested_display_precision=4,
    ),
    YieldSensorDescription(
        key="last_quarter_export_energy",
        native_unit=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:transmission-tower-export",
        value_fn=lambda a: a.last.export_energy_kwh,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_export_revenue",
        native_unit="EUR",
        icon="mdi:cash-plus",
        value_fn=lambda a: a.last.export_revenue_eur,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_self_supply_energy",
        native_unit=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:home-lightning-bolt",
        value_fn=lambda a: a.last.self_supply_energy_kwh,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_self_consumption_saving",
        native_unit="EUR",
        icon="mdi:home-currency-eur",
        value_fn=lambda a: a.last.self_consumption_saving_eur,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_grid_to_battery_energy",
        native_unit=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:battery-arrow-down",
        value_fn=lambda a: a.last.grid_to_battery_energy_kwh,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_grid_to_battery_cost",
        native_unit="EUR",
        icon="mdi:battery-minus",
        value_fn=lambda a: a.last.grid_to_battery_cost_eur,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
    YieldSensorDescription(
        key="last_quarter_total_benefit",
        native_unit="EUR",
        icon="mdi:cash-check",
        value_fn=lambda a: a.last.total_benefit_eur,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        quarter_total=True,
    ),
) + tuple(
    YieldSensorDescription(
        key=f"{period}_{key_suffix}",
        native_unit="EUR",
        icon=icon,
        value_fn=_period_value(period, field),
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=4,
        period=period,
    )
    for period in ("hour", "day", "month", "year")
    for key_suffix, field, icon in (
        ("export_revenue", "export_revenue_eur", "mdi:cash-plus"),
        ("self_consumption_saving", "self_consumption_saving_eur", "mdi:home-currency-eur"),
        ("grid_to_battery_cost", "grid_to_battery_cost_eur", "mdi:battery-minus"),
        ("total_benefit", "total_benefit_eur", "mdi:cash-check"),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up calculated sensors."""
    accounting: SolarYieldAccounting = hass.data[DOMAIN][entry.entry_id][DATA_ACCOUNTING]
    async_add_entities(
        SolarYieldCalculatorSensor(entry, accounting, description)
        for description in SENSORS
    )


class SolarYieldCalculatorSensor(SensorEntity):
    """A synchronized Solar Yield Calculator sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        accounting: SolarYieldAccounting,
        description: YieldSensorDescription,
    ) -> None:
        self.entry = entry
        self.accounting = accounting
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.key
        self._attr_native_unit_of_measurement = description.native_unit
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_suggested_display_precision = description.suggested_display_precision
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Solar Yield Calculator",
            "manufacturer": "futuremeetsreality",
            "model": "PV Yield Accounting",
            "sw_version": VERSION,
        }

    @property
    def native_value(self) -> Decimal | None:
        value = self._description.value_fn(self.accounting)
        return None if value is None else Decimal(str(round(value, 6)))

    @property
    def last_reset(self):
        """Return the active meter-cycle start."""
        if self._description.quarter_total:
            if not self.accounting.last.start:
                return None
            return dt_util.parse_datetime(self.accounting.last.start)
        if self._description.period:
            start = self.accounting.periods[self._description.period].start
            return dt_util.parse_datetime(start) if start else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose audit timestamps without changing on every power update."""
        if self._description.quarter_total:
            return {
                "interval_start": self.accounting.last.start,
                "interval_end": self.accounting.last.end,
            }
        if self._description.period:
            return {
                "period": self._description.period,
                "period_start": self.accounting.periods[self._description.period].start,
                "accounting_granularity": "completed_15_minute_intervals",
            }
        return None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.accounting.async_add_listener(self._handle_update))

    def _handle_update(self) -> None:
        self.async_write_ha_state()
