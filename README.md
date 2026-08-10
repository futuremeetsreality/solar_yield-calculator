# Solar Yield Calculator

Custom Home Assistant integration for transparent PV yield and savings calculations.

> Development status: **0.1.5-dev** — no public release yet.

## Current 0.1.5 development scope

- UI based setup through Home Assistant Config Flow.
- Source entity selection for house load, grid import/export, battery output, grid-to-battery energy and EPEX price.
- Net energy price can be entered manually or read dynamically from a Home Assistant sensor.
- Dynamic net energy price supports `ct/kWh`, `EUR/kWh` and `€/kWh`; the manual value remains the fallback if the entity is unavailable or has an unsupported unit.
- Editable tariff values through the integration options dialog.
- Gross grid price and effective EPEX price calculation.
- Synchronized live calculation snapshot for house self-supply, export revenue, self-consumption saving and total live benefit rate.
- Persistent 15-minute accounting stored by the integration.
- 15-minute export energy and EPEX-based export revenue.
- 15-minute self-supplied house energy and avoided gross grid cost.
- Grid-to-battery energy is separated from house grid import in the settlement calculation and its gross charging cost is deducted from total benefit.
- Current hour, day, month and year monetary totals for export revenue, self-consumption saving, grid-to-battery cost and total benefit.
- Completed quarters are deduplicated before being credited to period meters, preventing restart or reload double counting.
- All accounting timestamps are normalized to Home Assistant local time so UTC scheduler ticks cannot reset local hour/day/month/year totals.
- Four-decimal monetary display precision for audit-friendly checking.
- Interval and period timestamps exposed as entity attributes.
- Stable technical entity IDs are migrated automatically from early development IDs.
- Restart handling intentionally does not backfill unknown power or grid-to-battery movement while Home Assistant was offline.
- German and English entity-name translations.

## Dynamic net energy price

In the integration options, `Net energy price entity` / `Strompreis netto aus Entität` is optional. If selected, that sensor takes precedence over the manual net energy price. The manual value is retained as a fallback.

Example for the current project setup:

`sensor.strompreis_ct`

The effective value used by the calculator is exposed as:

`sensor.solar_yield_calculator_effective_energy_price_net`

## Accounting model

For each 15-minute settlement interval the integration integrates house load, grid import and grid export power. The selected `Grid to Battery Energy` counter is used to distinguish grid energy used to charge the battery from grid energy actually used by the house.

The resulting interval benefit is:

`export revenue + self-consumption saving - grid-to-battery cost`

Completed 15-minute intervals are accumulated into the active local calendar hour, day, month and year. Period sensors therefore represent completed settlement intervals only; the currently open quarter is added when it closes.

## Test dashboard

A copy-ready Home Assistant Entities Card is available at:

`examples/test_dashboard.yaml`

Copy the YAML content into a manual card in Home Assistant. It contains the live prices, current benefit rates, last completed 15-minute settlement and hour/day/month/year totals.

## Restart and upgrade behavior

The active partial quarter and completed totals are persisted. On restart, accounting resumes from the current source states. Energy or power changes that happened while Home Assistant was offline are not guessed or backfilled, preventing false spikes.

When upgrading from an early development version where the last completed quarter existed before period meters were initialized, empty matching active periods can be seeded from that persisted quarter. A per-period interval marker prevents the same quarter from being credited twice.

## Next development steps

- HACS/Hassfest validation workflows.
- Additional diagnostics for unusual source units or unavailable source sensors.
- Optional historical settlement detail beyond the last completed quarter.

## Development installation

During development, install the repository as a HACS custom integration repository after the current development branch has been merged to `main`.

## Versioning

Development uses semantic versions starting at `0.1.0`. GitHub Releases and tags are intentionally not used during the current development phase.
