"""Constants for Solar Yield Calculator."""

DOMAIN = "solar_yield_calculator"
VERSION = "0.1.5"

CONF_HOUSE_LOAD = "house_load"
CONF_GRID_IMPORT_POWER = "grid_import_power"
CONF_GRID_EXPORT_POWER = "grid_export_power"
CONF_BATTERY_OUTPUT_POWER = "battery_output_power"
CONF_GRID_TO_BATTERY_ENERGY = "grid_to_battery_energy"
CONF_EPEX_PRICE = "epex_price"
CONF_EPEX_UNIT = "epex_unit"

CONF_ENERGY_PRICE_NET = "energy_price_net"
CONF_ENERGY_PRICE_NET_ENTITY = "energy_price_net_entity"
CONF_NETWORK_FEE_NET = "network_fee_net"
CONF_TAXES_NET = "taxes_net"
CONF_VAT = "vat"
CONF_EPEX_ADJUSTMENT = "epex_adjustment"

EPEX_UNIT_EUR_KWH = "EUR/kWh"
EPEX_UNIT_CT_KWH = "ct/kWh"
EPEX_UNIT_EUR_MWH = "EUR/MWh"
EPEX_UNITS = (EPEX_UNIT_EUR_KWH, EPEX_UNIT_CT_KWH, EPEX_UNIT_EUR_MWH)

DEFAULT_ENERGY_PRICE_NET = 15.0
DEFAULT_NETWORK_FEE_NET = 10.0
DEFAULT_TAXES_NET = 4.0
DEFAULT_VAT = 20.0
DEFAULT_EPEX_ADJUSTMENT = 0.0

DATA_ACCOUNTING = "accounting"
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.accounting"
ACCOUNTING_TICK_SECONDS = 60

BASE_SENSOR_KEYS = (
    "grid_price_gross",
    "effective_epex_price",
    "effective_energy_price_net",
    "self_supply_power",
    "export_revenue_rate",
    "self_consumption_saving_rate",
    "total_benefit_rate",
    "last_quarter_export_energy",
    "last_quarter_export_revenue",
    "last_quarter_self_supply_energy",
    "last_quarter_self_consumption_saving",
    "last_quarter_grid_to_battery_energy",
    "last_quarter_grid_to_battery_cost",
    "last_quarter_total_benefit",
)

PERIOD_SENSOR_KEYS = tuple(
    f"{period}_{metric}"
    for period in ("hour", "day", "month", "year")
    for metric in (
        "export_revenue",
        "self_consumption_saving",
        "grid_to_battery_cost",
        "total_benefit",
    )
)

ENTITY_KEYS = BASE_SENSOR_KEYS + PERIOD_SENSOR_KEYS
