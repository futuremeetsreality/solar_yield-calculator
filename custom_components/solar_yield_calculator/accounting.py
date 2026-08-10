"""Persistent interval accounting for Solar Yield Calculator."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .calculations import (
    effective_epex_price_eur_kwh,
    gross_grid_price_eur_kwh,
    self_supply_energy_kwh,
)
from .const import (
    ACCOUNTING_TICK_SECONDS,
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
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)
PERIODS = ("hour", "day", "month", "year")


@dataclass
class LiveSnapshot:
    """One synchronized set of source values used for integration."""

    house_kw: float = 0.0
    grid_import_kw: float = 0.0
    grid_export_kw: float = 0.0
    epex_eur_kwh: float = 0.0
    grid_price_eur_kwh: float = 0.0


@dataclass
class QuarterTotals:
    """Accounting totals for one 15-minute settlement interval."""

    start: str = ""
    end: str = ""
    house_energy_kwh: float = 0.0
    grid_import_energy_kwh: float = 0.0
    grid_to_battery_energy_kwh: float = 0.0
    self_supply_energy_kwh: float = 0.0
    export_energy_kwh: float = 0.0
    export_revenue_eur: float = 0.0
    self_consumption_saving_eur: float = 0.0
    grid_to_battery_cost_eur: float = 0.0
    total_benefit_eur: float = 0.0


@dataclass
class PeriodTotals:
    """Money totals for the active accounting period."""

    start: str = ""
    export_revenue_eur: float = 0.0
    self_consumption_saving_eur: float = 0.0
    grid_to_battery_cost_eur: float = 0.0
    total_benefit_eur: float = 0.0
    last_interval_start: str = ""


class SolarYieldAccounting:
    """Integrate source states into synchronized persistent accounting totals."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}.{entry.entry_id}"
        )
        self.live = LiveSnapshot()
        self.current = QuarterTotals()
        self.last = QuarterTotals()
        self.periods: dict[str, PeriodTotals] = {
            period: PeriodTotals() for period in PERIODS
        }
        self._listeners: set[Callable[[], None]] = set()
        self._last_update: datetime | None = None
        self._last_grid_to_battery_raw: float | None = None
        self._unsubs: list[Callable[[], None]] = []

    async def async_start(self) -> None:
        """Load persisted data and start listeners."""
        stored = await self.store.async_load()
        if stored:
            self.last = QuarterTotals(**stored.get("last", {}))
            current = stored.get("current")
            if current:
                self.current = QuarterTotals(**current)
            stored_periods = stored.get("periods", {})
            for period in PERIODS:
                if stored_periods.get(period):
                    self.periods[period] = PeriodTotals(**stored_periods[period])

        now = dt_util.now()
        current_start = self._quarter_start(now)
        if self.current.start != current_start.isoformat():
            self.current = self._new_quarter(current_start)

        self._roll_periods(now)
        self._bootstrap_periods_from_last(now)
        self._last_update = now
        self._last_grid_to_battery_raw = self._grid_to_battery_value()
        self.live = self._read_live_snapshot()

        source_entities = {
            str(self.entry.data[key])
            for key in (
                CONF_HOUSE_LOAD,
                CONF_GRID_IMPORT_POWER,
                CONF_GRID_EXPORT_POWER,
                CONF_GRID_TO_BATTERY_ENERGY,
                CONF_EPEX_PRICE,
            )
        }
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, source_entities, self._async_source_changed
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_tick,
                timedelta(seconds=ACCOUNTING_TICK_SECONDS),
            )
        )
        await self._async_save()

    async def async_stop(self) -> None:
        """Stop listeners after accounting up to unload time."""
        await self.async_update()
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._async_save()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a sensor update listener."""
        self._listeners.add(listener)

        def _remove() -> None:
            self._listeners.discard(listener)

        return _remove

    async def _async_source_changed(self, event: Event[EventStateChangedData]) -> None:
        """Account previous synchronized values before accepting new source states."""
        await self.async_update()

    async def _async_tick(self, now: datetime) -> None:
        """Periodic safety tick so unchanged states still accrue energy."""
        await self.async_update(now)

    async def async_update(self, now: datetime | None = None) -> None:
        """Integrate elapsed time, roll quarter boundaries and publish a snapshot."""
        now = now or dt_util.now()
        if self._last_update is None:
            self._last_update = now
            self.live = self._read_live_snapshot()
            return
        if now <= self._last_update:
            return

        grid_raw_now = self._grid_to_battery_value()
        grid_delta_total = self._counter_delta(
            self._last_grid_to_battery_raw, grid_raw_now
        )
        total_seconds = (now - self._last_update).total_seconds()

        cursor = self._last_update
        while cursor < now:
            boundary = self._quarter_start(cursor) + timedelta(minutes=15)
            segment_end = min(boundary, now)
            seconds = (segment_end - cursor).total_seconds()
            fraction = seconds / total_seconds if total_seconds > 0 else 0.0
            self._integrate_segment(seconds, grid_delta_total * fraction)
            cursor = segment_end
            if cursor >= boundary:
                self._finalize_current(boundary)

        self._roll_periods(now)
        self._last_update = now
        self._last_grid_to_battery_raw = grid_raw_now
        self.live = self._read_live_snapshot()
        await self._async_save()
        self._notify_listeners()

    def _integrate_segment(self, seconds: float, grid_to_battery_delta_kwh: float) -> None:
        """Integrate one segment that does not cross a quarter boundary."""
        hours = seconds / 3600.0
        if hours <= 0:
            return

        house_delta = max(self.live.house_kw, 0.0) * hours
        grid_import_delta = max(self.live.grid_import_kw, 0.0) * hours
        export_delta = max(self.live.grid_export_kw, 0.0) * hours
        grid_to_battery_delta_kwh = max(grid_to_battery_delta_kwh, 0.0)
        self_supply_delta = self_supply_energy_kwh(
            house_delta, grid_import_delta, grid_to_battery_delta_kwh
        )

        self.current.house_energy_kwh += house_delta
        self.current.grid_import_energy_kwh += grid_import_delta
        self.current.grid_to_battery_energy_kwh += grid_to_battery_delta_kwh
        self.current.self_supply_energy_kwh += self_supply_delta
        self.current.export_energy_kwh += export_delta
        self.current.export_revenue_eur += export_delta * self.live.epex_eur_kwh
        self.current.self_consumption_saving_eur += (
            self_supply_delta * self.live.grid_price_eur_kwh
        )
        self.current.grid_to_battery_cost_eur += (
            grid_to_battery_delta_kwh * self.live.grid_price_eur_kwh
        )

    def _finalize_current(self, boundary: datetime) -> None:
        """Close the current quarter and add it to active period totals."""
        self.current.end = boundary.isoformat()
        self.current.total_benefit_eur = (
            self.current.export_revenue_eur
            + self.current.self_consumption_saving_eur
            - self.current.grid_to_battery_cost_eur
        )
        self.last = self._rounded_quarter(self.current)
        quarter_start = dt_util.parse_datetime(self.last.start) or boundary - timedelta(minutes=15)
        self._add_quarter_to_periods(self.last, quarter_start)
        self.current = self._new_quarter(boundary)

    def _add_quarter_to_periods(
        self, quarter: QuarterTotals, quarter_start: datetime
    ) -> None:
        """Credit one completed quarter exactly once to each matching period."""
        if not quarter.start:
            return

        for period in PERIODS:
            expected = self._period_start(period, quarter_start)
            if self.periods[period].start != expected.isoformat():
                self.periods[period] = PeriodTotals(start=expected.isoformat())

            totals = self.periods[period]
            if totals.last_interval_start == quarter.start:
                continue

            totals.export_revenue_eur += quarter.export_revenue_eur
            totals.self_consumption_saving_eur += quarter.self_consumption_saving_eur
            totals.grid_to_battery_cost_eur += quarter.grid_to_battery_cost_eur
            totals.total_benefit_eur += quarter.total_benefit_eur
            totals.last_interval_start = quarter.start

    def _bootstrap_periods_from_last(self, now: datetime) -> None:
        """Seed empty 0.1.2 period meters from the persisted last quarter once.

        Version 0.1.2 introduced period meters after quarter persistence already
        existed. Immediately after upgrading, the last-quarter sensors could
        therefore contain a valid settlement while all period meters were zero.
        Only empty active periods are seeded, so existing non-zero totals are
        never duplicated.
        """
        if not self.last.start:
            return

        quarter_start = dt_util.parse_datetime(self.last.start)
        if quarter_start is None:
            return

        for period in PERIODS:
            quarter_period_start = self._period_start(period, quarter_start)
            active_period_start = self._period_start(period, now)
            if quarter_period_start != active_period_start:
                continue

            totals = self.periods[period]
            if totals.start != active_period_start.isoformat():
                continue
            if totals.last_interval_start == self.last.start:
                continue
            if not self._period_is_empty(totals):
                continue

            totals.export_revenue_eur = self.last.export_revenue_eur
            totals.self_consumption_saving_eur = self.last.self_consumption_saving_eur
            totals.grid_to_battery_cost_eur = self.last.grid_to_battery_cost_eur
            totals.total_benefit_eur = self.last.total_benefit_eur
            totals.last_interval_start = self.last.start

    @staticmethod
    def _period_is_empty(totals: PeriodTotals) -> bool:
        """Return whether a period has no credited monetary settlement yet."""
        return all(
            abs(value) < 1e-12
            for value in (
                totals.export_revenue_eur,
                totals.self_consumption_saving_eur,
                totals.grid_to_battery_cost_eur,
                totals.total_benefit_eur,
            )
        )

    def _roll_periods(self, now: datetime) -> None:
        """Reset active period meters at their calendar boundaries."""
        for period in PERIODS:
            expected = self._period_start(period, now)
            if self.periods[period].start != expected.isoformat():
                self.periods[period] = PeriodTotals(start=expected.isoformat())

    def _new_quarter(self, start: datetime) -> QuarterTotals:
        return QuarterTotals(
            start=start.isoformat(),
            end=(start + timedelta(minutes=15)).isoformat(),
        )

    def _read_live_snapshot(self) -> LiveSnapshot:
        return LiveSnapshot(
            house_kw=self._power_kw(self.entry.data[CONF_HOUSE_LOAD]),
            grid_import_kw=self._power_kw(self.entry.data[CONF_GRID_IMPORT_POWER]),
            grid_export_kw=self._power_kw(self.entry.data[CONF_GRID_EXPORT_POWER]),
            epex_eur_kwh=self._epex_price(),
            grid_price_eur_kwh=self._grid_price(),
        )

    def _power_kw(self, entity_id: str) -> float:
        state = self.hass.states.get(str(entity_id))
        value = self._state_float(state)
        if value is None or state is None:
            return 0.0
        unit = state.attributes.get("unit_of_measurement")
        if unit == "W":
            return value / 1000.0
        if unit == "kW":
            return value
        _LOGGER.warning("Unsupported power unit %s for %s", unit, entity_id)
        return 0.0

    def _grid_to_battery_value(self) -> float | None:
        state = self.hass.states.get(str(self.entry.data[CONF_GRID_TO_BATTERY_ENERGY]))
        value = self._state_float(state)
        if value is None or state is None:
            return None
        unit = state.attributes.get("unit_of_measurement")
        if unit == "Wh":
            return value / 1000.0
        if unit == "kWh":
            return value
        if unit == "MWh":
            return value * 1000.0
        _LOGGER.warning(
            "Unsupported energy unit %s for %s",
            unit,
            self.entry.data[CONF_GRID_TO_BATTERY_ENERGY],
        )
        return None

    @staticmethod
    def _state_float(state: State | None) -> float | None:
        if state is None or state.state in {"unknown", "unavailable"}:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _counter_delta(previous: float | None, current: float | None) -> float:
        if previous is None or current is None:
            return 0.0
        if current >= previous:
            return current - previous
        return max(current, 0.0)

    def _grid_price(self) -> float:
        return gross_grid_price_eur_kwh(
            self._option(CONF_ENERGY_PRICE_NET, DEFAULT_ENERGY_PRICE_NET),
            self._option(CONF_NETWORK_FEE_NET, DEFAULT_NETWORK_FEE_NET),
            self._option(CONF_TAXES_NET, DEFAULT_TAXES_NET),
            self._option(CONF_VAT, DEFAULT_VAT),
        )

    def _epex_price(self) -> float:
        raw = self._state_float(self.hass.states.get(str(self.entry.data[CONF_EPEX_PRICE])))
        if raw is None:
            return 0.0
        return effective_epex_price_eur_kwh(
            raw,
            str(self.entry.data[CONF_EPEX_UNIT]),
            self._option(CONF_EPEX_ADJUSTMENT, DEFAULT_EPEX_ADJUSTMENT),
        )

    def _option(self, key: str, default: float) -> float:
        return float(self.entry.options.get(key, self.entry.data.get(key, default)))

    @staticmethod
    def _quarter_start(value: datetime) -> datetime:
        minute = (value.minute // 15) * 15
        return value.replace(minute=minute, second=0, microsecond=0)

    @staticmethod
    def _period_start(period: str, value: datetime) -> datetime:
        if period == "hour":
            return value.replace(minute=0, second=0, microsecond=0)
        if period == "day":
            return value.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "month":
            return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period == "year":
            return value.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        raise ValueError(f"Unsupported period: {period}")

    @staticmethod
    def _rounded_quarter(value: QuarterTotals) -> QuarterTotals:
        data = asdict(value)
        for key, item in data.items():
            if isinstance(item, float):
                data[key] = round(item, 6)
        return QuarterTotals(**data)

    @staticmethod
    def _rounded_period(value: PeriodTotals) -> PeriodTotals:
        data = asdict(value)
        for key, item in data.items():
            if isinstance(item, float):
                data[key] = round(item, 6)
        return PeriodTotals(**data)

    async def _async_save(self) -> None:
        await self.store.async_save(
            {
                "current": asdict(self._rounded_quarter(self.current)),
                "last": asdict(self._rounded_quarter(self.last)),
                "periods": {
                    period: asdict(self._rounded_period(totals))
                    for period, totals in self.periods.items()
                },
            }
        )

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()
