"""Config flow for Solar Yield Calculator."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_BATTERY_OUTPUT_POWER,
    CONF_ENERGY_PRICE_NET,
    CONF_EPEX_ADJUSTMENT,
    CONF_EPEX_PRICE,
    CONF_EPEX_UNIT,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_TO_BATTERY_ENERGY,
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
    EPEX_UNIT_CT_KWH,
    EPEX_UNITS,
)


def _entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=["sensor"]))


def _number_selector(minimum: float, maximum: float, step: float) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


class SolarYieldCalculatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Yield Calculator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Solar Yield Calculator", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOUSE_LOAD): _entity_selector(),
                vol.Required(CONF_GRID_IMPORT_POWER): _entity_selector(),
                vol.Required(CONF_GRID_EXPORT_POWER): _entity_selector(),
                vol.Required(CONF_BATTERY_OUTPUT_POWER): _entity_selector(),
                vol.Required(CONF_GRID_TO_BATTERY_ENERGY): _entity_selector(),
                vol.Required(CONF_EPEX_PRICE): _entity_selector(),
                vol.Required(CONF_EPEX_UNIT, default=EPEX_UNIT_CT_KWH): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(EPEX_UNITS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_ENERGY_PRICE_NET, default=DEFAULT_ENERGY_PRICE_NET): _number_selector(0, 100, 0.01),
                vol.Required(CONF_NETWORK_FEE_NET, default=DEFAULT_NETWORK_FEE_NET): _number_selector(0, 100, 0.01),
                vol.Required(CONF_TAXES_NET, default=DEFAULT_TAXES_NET): _number_selector(0, 100, 0.01),
                vol.Required(CONF_VAT, default=DEFAULT_VAT): _number_selector(0, 30, 0.1),
                vol.Required(CONF_EPEX_ADJUSTMENT, default=DEFAULT_EPEX_ADJUSTMENT): _number_selector(-50, 50, 0.01),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return SolarYieldCalculatorOptionsFlow(config_entry)


class SolarYieldCalculatorOptionsFlow(config_entries.OptionsFlow):
    """Handle editable tariff options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    def _value(self, key: str, default: float) -> float:
        return float(self._entry.options.get(key, self._entry.data.get(key, default)))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit tariff values."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_ENERGY_PRICE_NET, default=self._value(CONF_ENERGY_PRICE_NET, DEFAULT_ENERGY_PRICE_NET)): _number_selector(0, 100, 0.01),
                vol.Required(CONF_NETWORK_FEE_NET, default=self._value(CONF_NETWORK_FEE_NET, DEFAULT_NETWORK_FEE_NET)): _number_selector(0, 100, 0.01),
                vol.Required(CONF_TAXES_NET, default=self._value(CONF_TAXES_NET, DEFAULT_TAXES_NET)): _number_selector(0, 100, 0.01),
                vol.Required(CONF_VAT, default=self._value(CONF_VAT, DEFAULT_VAT)): _number_selector(0, 30, 0.1),
                vol.Required(CONF_EPEX_ADJUSTMENT, default=self._value(CONF_EPEX_ADJUSTMENT, DEFAULT_EPEX_ADJUSTMENT)): _number_selector(-50, 50, 0.01),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
