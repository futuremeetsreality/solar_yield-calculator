# Solar Yield Calculator

Custom Home Assistant integration for transparent PV yield and savings calculations.

> Development status: **0.1.1-dev** — no public release yet.

## Current 0.1.1 development scope

- UI based setup through Home Assistant Config Flow.
- Source entity selection for house load, grid import/export, battery output, grid-to-battery energy and EPEX price.
- Editable tariff values through the integration options dialog.
- Gross grid price and effective EPEX price calculation.
- Synchronized live calculation snapshot for house self-supply, export revenue, self-consumption saving and total live benefit rate.
- Persistent 15-minute accounting stored by the integration.
- 15-minute export energy and EPEX-based export revenue.
- 15-minute self-supplied house energy and avoided gross grid cost.
- Grid-to-battery energy is separated from house grid import in the settlement calculation and its gross charging cost is deducted from total benefit.
- German and English entity-name translations.

## 15-minute accounting model

For each settlement interval the integration integrates house load, grid import and grid export power. The selected `Grid to Battery Energy` counter is used to distinguish grid energy used to charge the battery from grid energy actually used by the house.

The resulting interval benefit is:

`export revenue + self-consumption saving - grid-to-battery cost`

The last completed interval is exposed as dedicated Home Assistant sensors and persisted across restarts.

## Next development steps

- Hourly, daily, monthly and yearly totals.
- Extended audit/diagnostic entities and calculation attributes.
- HACS/Hassfest validation workflows.
- Additional handling and diagnostics for unusual source units or unavailable source sensors.

## Development installation

During development, install the repository as a HACS custom integration repository after the current development branch has been merged to `main`.

## Versioning

Development uses semantic versions starting at `0.1.0`. GitHub Releases and tags are intentionally not used during the current development phase.
