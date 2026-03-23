# US Tax Advisor — Claude Code Guide

## Purpose

General-purpose US tax analysis toolkit. Claude Code skill handles conversation (questions, document reading, scenario comparison). Python scripts handle pure calculations.

## Architecture

- **Skill** (`skills/tax-analysis.md`): Orchestrates analysis — asks user questions, reads documents, calls scripts, presents results
- **Scripts** (`scripts/`): Stateless calculators — numbers in, numbers out. No user interaction.
- **Docs** (`docs/`): Reference material for tax rules, strategies, and common mistakes

## Key Rules

- Never give definitive tax advice — always recommend professional verification
- Keep the tool general — don't hardcode specific visa types, treaty countries, or personal scenarios
- All monetary amounts in USD, round to whole dollars in output
- Tax year defaults to 2025 unless specified
- When reading tax documents, extract numbers carefully — PDF text extraction can jumble W-2 fields
- Always present multiple scenarios side-by-side
- Flag uncertainties rather than assuming

## Script Conventions

- Python 3.10+, no external dependencies (stdlib only)
- All functions take explicit parameters, no global state
- Return dictionaries with labeled results
- Include docstrings with parameter descriptions
- Scenario configs use JSON files (see examples/)

## Adding New Tax Years

Update these constants in the scripts:
- `BRACKETS` and `QD_BRACKETS` in `brackets.py`
- `SALT_CAP` and `STANDARD_DEDUCTION` in `deductions.py`
- Verify thresholds for Additional Medicare Tax and NIIT
