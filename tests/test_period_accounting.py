# Datei: tests/test_period_accounting.py
# Zeitstempel: 2026-08-10 07:40 CEST

"""Regression tests for period settlement accounting."""

from datetime import datetime, timezone

from custom_components.solar_yield_calculator.accounting import (
    PERIODS,
    PeriodTotals,
    QuarterTotals,
    SolarYieldAccounting,
)


def _accounting() -> SolarYieldAccounting:
    accounting = SolarYieldAccounting.__new__(SolarYieldAccounting)
    accounting.periods = {period: PeriodTotals() for period in PERIODS}
    accounting.last = QuarterTotals()
    return accounting


def _quarter(start: str, benefit: float = 0.0439) -> QuarterTotals:
    return QuarterTotals(
        start=start,
        export_revenue_eur=0.0065,
        self_consumption_saving_eur=0.0374,
        grid_to_battery_cost_eur=0.0,
        total_benefit_eur=benefit,
    )


def test_completed_quarter_is_credited_once() -> None:
    accounting = _accounting()
    start = datetime(2026, 8, 10, 7, 15, tzinfo=timezone.utc)
    quarter = _quarter(start.isoformat())

    accounting._add_quarter_to_periods(quarter, start)
    accounting._add_quarter_to_periods(quarter, start)

    assert accounting.periods["hour"].total_benefit_eur == 0.0439
    assert accounting.periods["day"].total_benefit_eur == 0.0439
    assert accounting.periods["month"].total_benefit_eur == 0.0439
    assert accounting.periods["year"].total_benefit_eur == 0.0439


def test_bootstrap_seeds_empty_active_periods_from_last_quarter() -> None:
    accounting = _accounting()
    start = datetime(2026, 8, 10, 7, 15, tzinfo=timezone.utc)
    now = datetime(2026, 8, 10, 7, 31, tzinfo=timezone.utc)
    accounting.last = _quarter(start.isoformat())
    accounting._roll_periods(now)

    accounting._bootstrap_periods_from_last(now)
    accounting._bootstrap_periods_from_last(now)

    assert accounting.periods["hour"].total_benefit_eur == 0.0439
    assert accounting.periods["day"].total_benefit_eur == 0.0439
    assert accounting.periods["month"].total_benefit_eur == 0.0439
    assert accounting.periods["year"].total_benefit_eur == 0.0439


def test_bootstrap_does_not_overwrite_existing_period_totals() -> None:
    accounting = _accounting()
    start = datetime(2026, 8, 10, 7, 15, tzinfo=timezone.utc)
    now = datetime(2026, 8, 10, 7, 31, tzinfo=timezone.utc)
    accounting.last = _quarter(start.isoformat())
    accounting._roll_periods(now)
    accounting.periods["day"].total_benefit_eur = 1.2345

    accounting._bootstrap_periods_from_last(now)

    assert accounting.periods["day"].total_benefit_eur == 1.2345
    assert accounting.periods["hour"].total_benefit_eur == 0.0439


def test_hour_rollover_does_not_reset_day_month_or_year() -> None:
    accounting = _accounting()
    start = datetime(2026, 8, 10, 7, 45, tzinfo=timezone.utc)
    quarter = _quarter(start.isoformat())
    accounting._add_quarter_to_periods(quarter, start)

    accounting._roll_periods(datetime(2026, 8, 10, 8, 0, tzinfo=timezone.utc))

    assert accounting.periods["hour"].total_benefit_eur == 0.0
    assert accounting.periods["day"].total_benefit_eur == 0.0439
    assert accounting.periods["month"].total_benefit_eur == 0.0439
    assert accounting.periods["year"].total_benefit_eur == 0.0439
