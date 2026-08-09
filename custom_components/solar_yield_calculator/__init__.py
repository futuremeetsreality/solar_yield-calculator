"""Solar Yield Calculator integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .accounting import SolarYieldAccounting
from .const import DATA_ACCOUNTING, DOMAIN, ENTITY_KEYS

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solar Yield Calculator from a config entry."""
    _migrate_entity_ids(hass, entry)

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


def _migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Normalize early-development entity IDs to stable technical IDs."""
    registry = er.async_get(hass)
    for key in ENTITY_KEYS:
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is None:
            continue

        desired = f"sensor.{DOMAIN}_{key}"
        if entity_id == desired or registry.async_get(desired) is not None:
            continue

        registry.async_update_entity(entity_id, new_entity_id=desired)
