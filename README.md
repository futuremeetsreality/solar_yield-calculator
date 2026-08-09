# Solar Yield Calculator

Custom Home Assistant integration for transparent PV yield and savings calculations.

> Development status: **0.1.2-dev** — no public release yet.

## Current 0.1.2 development scope

- UI based setup through Home Assistant Config Flow.
- Source entity selection for house load, grid import/export, battery output, grid-to-battery energy and EPEX price.
- Editable tariff values through the integration options dialog.
- Gross grid price and effective EPEX price calculation.
- Synchronized live calculation snapshot for house self-supply, export revenue, self-consumption saving and total live benefit rate.
- Persistent 15-minute accounting stored by the integration.
- 15-minute export energy and EPEX-based export revenue.
- 15-minute self-supplied house energy and avoided gross grid cost.
- Grid-to-battery energy is separated from house grid import in the settlement calculation and its gross charging cost is deducted from total benefit.
- Current hour, day, month and year monetary totals for export revenue, self-consumption saving, grid-to-battery cost and total benefit.
- Four-decimal monetary display precision for audit-friendly checking.
- Interval and period timestamps exposed as entity attributes.
- Stable technical entity IDs are migrated automatically from early development IDs.
- Restart handling intentionally does not backfill unknown power or grid-to-battery movement while Home Assistant was offline.
- German and English entity-name translations.

## Accounting model

For each 15-minute settlement interval the integration integrates house load, grid import and grid export power. The selected `Grid to Battery Energy` counter is used to distinguish grid energy used to charge the battery from grid energy actually used by the house.

The resulting interval benefit is:

`export revenue + self-consumption saving - grid-to-battery cost`

Completed 15-minute intervals are accumulated into the active calendar hour, day, month and year. Period sensors therefore represent completed settlement intervals only; the currently open quarter is added when it closes.

## Restart behavior

The active partial quarter and completed totals are persisted. On restart, accounting resumes from the current source states. Energy or power changes that happened while Home Assistant was offline are not guessed or backfilled, preventing false spikes.

## Next development steps

- HACS/Hassfest validation workflows.
- Additional diagnostics for unusual source units or unavailable source sensors.
- Optional historical settlement detail beyond the last completed quarter.

## Development installation

During development, install the repository as a HACS custom integration repository after the current development branch has been merged to `main`.

## Versioning

Development uses semantic versions starting at `0.1.0`. GitHub Releases and tags are intentionally not used during the current development phase.
