# Solar Yield Calculator

Custom Home Assistant integration for transparent PV yield and savings calculations.

> Development status: **0.1.0-dev** — no public release yet.

## Current 0.1.0 development scope

- UI based setup through Home Assistant Config Flow.
- Source entity selection for house load, grid import/export, battery output, grid-to-battery energy and EPEX price.
- Editable tariff values through the integration options dialog.
- Gross grid price calculation.
- Effective EPEX price calculation with selectable input unit and optional adjustment.
- Live self-supplied house power, export revenue rate, self-consumption saving rate and combined benefit rate.
- German and English UI translations.

## Next development steps

- Persistent 15-minute accounting.
- Hourly, daily, monthly and yearly totals.
- Grid-to-battery cost accounting.
- Auditable diagnostic entities and calculation attributes.
- HACS/Hassfest validation workflows.

## Development installation

During development, install the repository as a HACS custom integration repository after the current development branch has been merged to `main`.

## Versioning

Development uses semantic versions starting at `0.1.0`. GitHub Releases are intentionally not used during the current development phase.
