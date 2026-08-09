"""Solar Yield Calculator integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .accounting import SolarYieldAccounting
from .const import DATA_ACCOUNTING, DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solar Yield Calculator from a config entry."""
    accounting = SolarYieldAccounting(hass, entry)
    await accounting.async_start()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_ACCOUNTING: accounting}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        accounting: SolarYieldAccounting = hass.data[DOMAIN][entry.entry_id][DATA_ACCOUNTING]
        await accounting.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
