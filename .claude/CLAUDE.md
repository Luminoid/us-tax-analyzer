# US Tax Analyzer -- Claude Code Guide

## Purpose

General-purpose US tax analysis toolkit. Claude Code skill handles conversation (questions, document reading, scenario comparison). Python scripts handle pure calculations.

## Architecture

- **Skill** (`skills/tax-analyzer.md`): Self-contained analysis flow -- reads documents first, auto-extracts data, asks only missing questions, calls scripts, presents results. Includes all filing strategy, deduction, and error-checking reference inline.
- **Scripts** (`scripts/`): Stateless calculators -- numbers in, numbers out. No user interaction.
  - `federal.py` -- Federal tax brackets, QD/LTCG rates, Medicare, NIIT
  - `state.py` -- State income tax (37 states + DC + NYC local)
  - `deductions.py` -- SALT cap, mortgage limits, itemized vs standard
  - `compare.py` -- Multi-scenario comparison (federal + state)
- **Examples** (`examples/`): Sample JSON configs for compare.py
  - `scenario-config.json` -- MFJ vs MFS with combined scenario
  - `nra-vs-mfj-config.json` -- NRA separate vs 6013(g) MFJ with state adjustments

## Key Rules

- Never give definitive tax advice -- always recommend professional verification
- Keep the tool general -- don't hardcode specific visa types, treaty countries, or personal scenarios
- All monetary amounts in USD, round to whole dollars in output
- Tax year defaults to 2025 unless specified
- When reading tax documents, extract numbers carefully -- PDF text extraction can jumble W-2 fields
- Always present multiple scenarios side-by-side
- Flag uncertainties rather than assuming

## Scenario Config Features

JSON configs for `compare.py` support:

- **`state_itemized_deductions`**: Override state deductions with `{mortgage_interest, property_tax, car_vlf, other}`. Bypasses state standard deduction. Needed when state allows deductions that federal NRA rules disallow (e.g., CA allows mortgage interest for federal NRAs).
- **`state_treaty_addback`**: Amount to add back to state AGI when state doesn't honor federal treaty exemptions (e.g., CA doesn't honor US-China Article 20 $5,000 exemption).
- **`state_income_adjustment`**: Amount to subtract from state AGI (e.g., own-state refund that's taxable federally but not on state return).
- **`combined`**: Top-level array of `{name, members}` groups. Combines member scenarios into a single aggregated row for comparison (e.g., "Spouse A NRA + Spouse B NRA" vs "MFJ").

## Script Conventions

- Python 3.10+, no external dependencies (stdlib only)
- All functions take explicit parameters, no global state
- Return dictionaries with labeled results
- Include docstrings with parameter descriptions
- Scenario configs use JSON files (see examples/)

## Adding New Tax Years

Update these constants in the scripts:
- `BRACKETS` and `QD_BRACKETS` in `federal.py`
- `SALT_CAP` and `STANDARD_DEDUCTION` in `deductions.py`
- State brackets in `state.py` (PROGRESSIVE_BRACKETS, FLAT_RATE, STATE_STANDARD_DEDUCTION)
- Verify thresholds for Additional Medicare Tax and NIIT
