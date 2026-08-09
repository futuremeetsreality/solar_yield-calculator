"""Sensor platform for Solar Yield Calculator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .calculations import (
    effective_epex_price_eur_kwh,
    export_revenue_rate_eur_h,
    gross_grid_price_eur_kwh,
    self_consumption_saving_rate_eur_h,
    self_supply_power_kw,
)
from .const import (
    CONF_ENERGY_PRICE_NET,
    CONF_EPEX_ADJUSTMENT,
    CONF_EPEX_PRICE,
    CONF_EPEX_UNIT,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_IMPORT_POWER,
    CONF_HOUSE_LOAD,
    CONF_NETWORK_FEE_NET,
    CONF_TAXES_NET,
    CONF_VAT,
    DEFAULT_ENERGY_PRICE_NET,
    DEFAULT_EPEX_ADJUSTMENT,
    DEFAULT_NETWORK_FEE_NET,
    DEFAULT_TAXES_NET,
    DEFAULT_VAT,
    DOMAIN,
    VERSION,
)


@dataclass(frozen=True, kw_only=True)
class YieldSensorDescription:
    """Description for a calculated sensor."""
    key: str
    name: str
    native_unit: str
    icon: str
    value_fn: Callable[["SolarYieldCalculatorSensor"], float | None]
    device_class: SensorDeviceClass | None = None


def _to_float(state: State | None) -> float | None:
    if state is None or state.state in {"unknown", "unavailable"}:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _power_kw(state: State | None) -> float | None:
    value = _to_float(state)
    if value is None or state is None:
        return None
    unit = state.attributes.get("unit_of_measurement")
    if unit == "W":
        return value / 1000.0
    if unit == "kW":
        return value
    return None


def _grid_price(entity: "SolarYieldCalculatorSensor") -> float:
    return gross_grid_price_eur_kwh(
        entity.option(CONF_ENERGY_PRICE_NET, DEFAULT_ENERGY_PRICE_NET),
        entity.option(CONF_NETWORK_FEE_NET, DEFAULT_NETWORK_FEE_NET),
        entity.option(CONF_TAXES_NET, DEFAULT_TAXES_NET),
        entity.option(CONF_VAT, DEFAULT_VAT),
    )


def _epex_price(entity: "SolarYieldCalculatorSensor") -> float | None:
    raw = _to_float(entity.source(CONF_EPEX_PRICE))
    if raw is None:
        return None
    return effective_epex_price_eur_kwh(
        raw,
        str(entity.entry.data[CONF_EPEX_UNIT]),
        entity.option(CONF_EPEX_ADJUSTMENT, DEFAULT_EPEX_ADJUSTMENT),
    )


def _self_supply(entity: "SolarYieldCalculatorSensor") -> float | None:
    house = _power_kw(entity.source(CONF_HOUSE_LOAD))
    grid_import = _power_kw(entity.source(CONF_GRID_IMPORT_POWER))
    if house is None or grid_import is None:
        return None
    return self_supply_power_kw(house, grid_import)


def _export_rate(entity: "SolarYieldCalculatorSensor") -> float | None:
    export = _power_kw(entity.source(CONF_GRID_EXPORT_POWER))
    price = _epex_price(entity)
    if export is None or price is None:
        return None
    return export_revenue_rate_eur_h(export, price)


def _saving_rate(entity: "SolarYieldCalculatorSensor") -> float | None:
    supply = _self_supply(entity)
    if supply is None:
        return None
    return self_consumption_saving_rate_eur_h(supply, _grid_price(entity))


def _total_rate(entity: "SolarYieldCalculatorSensor") -> float | None:
    export = _export_rate(entity)
    saving = _saving_rate(entity)
    if export is None or saving is None:
        return None
    return export + saving


SENSORS = (
    YieldSensorDescription(key="grid_price_gross", name="Grid price gross", native_unit="EUR/kWh", icon="mdi:cash", value_fn=_grid_price),
    YieldSensorDescription(key="effective_epex_price", name="Effective EPEX price", native_unit="EUR/kWh", icon="mdi:chart-line", value_fn=_epex_price),
    YieldSensorDescription(key="self_supply_power", name="Self supplied house power", native_unit=UnitOfPower.KILO_WATT, icon="mdi:home-lightning-bolt", value_fn=_self_supply, device_class=SensorDeviceClass.POWER),
    YieldSensorDescription(key="export_revenue_rate", name="Export revenue rate", native_unit="EUR/h", icon="mdi:cash-plus", value_fn=_export_rate),
    YieldSensorDescription(key="self_consumption_saving_rate", name="Self consumption saving rate", native_unit="EUR/h", icon="mdi:home-currency-eur", value_fn=_saving_rate),
    YieldSensorDescription(key="total_benefit_rate", name="Total benefit rate", native_unit="EUR/h", icon="mdi:cash-check", value_fn=_total_rate),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Set up calculated sensors."""
    async_add_entities(SolarYieldCalculatorSensor(hass, entry, description) for description in SENSORS)


class SolarYieldCalculatorSensor(SensorEntity):
    """A calculated Solar Yield Calculator sensor."""
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, description: YieldSensorDescription) -> None:
        self.hass = hass
        self.entry = entry
        self._description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.native_unit
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Solar Yield Calculator",
            "manufacturer": "futuremeetsreality",
            "model": "PV Yield Accounting",
            "sw_version": VERSION,
        }

    def source(self, key: str) -> State | None:
        return self.hass.states.get(str(self.entry.data[key]))

    def option(self, key: str, default: float) -> float:
        return float(self.entry.options.get(key, self.entry.data.get(key, default)))

    @property
    def available(self) -> bool:
        return self._description.value_fn(self) is not None

    @property
    def native_value(self) -> Decimal | None:
        value = self._description.value_fn(self)
        return None if value is None else Decimal(str(round(value, 6)))

    async def async_added_to_hass(self) -> None:
        source_entities = {
            str(value)
            for key, value in self.entry.data.items()
            if key in {CONF_HOUSE_LOAD, CONF_GRID_IMPORT_POWER, CONF_GRID_EXPORT_POWER, CONF_EPEX_PRICE}
        }
        self.async_on_remove(async_track_state_change_event(self.hass, source_entities, self._async_source_changed))

    async def _async_source_changed(self, event: Event[EventStateChangedData]) -> None:
        self.async_write_ha_state()
