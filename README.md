# US Tax Analyzer

A Claude Code skill + Python toolkit for US federal and state income tax analysis. Compares filing scenarios, calculates deductions, and reviews returns for errors.

## What It Does

1. **Reads tax documents** (W-2, 1099, 1098, 1042-S) from a folder you provide
2. **Auto-extracts** income, withholding, deductions, and state -- asks only what's missing
3. **Calculates federal + state tax** under multiple filing scenarios
4. **Compares scenarios** side-by-side with a clear recommendation
5. **Reviews prepared returns** -- flags errors, missing deductions, and suboptimal strategies

## Prerequisites

- **Python 3.10+** (no external dependencies -- stdlib only)
- **poppler** (recommended -- fallback for reading tax document PDFs if Claude Code's native PDF reader fails)

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

## Setup

### Option 1: As a Claude Code Skill (Recommended)

Copy the skill into any project where you want tax analysis:

```bash
# Clone the repo
git clone https://github.com/anthropics/us-tax-analyzer.git

# Copy skill to your project
mkdir -p your-project/.claude/skills/tax-analyzer/
cp us-tax-analyzer/skills/tax-analyzer.md your-project/.claude/skills/tax-analyzer/SKILL.md
```

Then in Claude Code, invoke: `/tax-analyzer`

The skill will:
1. Ask for your document folder, marital status, citizenship status, and dependents
2. Read and auto-extract data from all tax documents (income, withholding, deductions, state)
3. Present a summary and ask only for what's missing (filing status, charitable contributions, etc.)
4. Search the web for the latest tax rules
5. Run the Python scripts to calculate and compare federal + state scenarios
6. Present a recommendation

### Option 2: Python Scripts (Standalone)

```bash
# Clone and use directly
git clone https://github.com/anthropics/us-tax-analyzer.git
cd us-tax-analyzer/scripts

# Calculate federal tax
python3 federal.py --income 150000 --status mfj --year 2025

# Calculate state tax
python3 state.py --state CA --income 150000 --status mfj --year 2025

# Calculate deductions
python3 deductions.py --state-tax 12000 --property-tax 8000 \
    --mortgage-interest 25000 --status mfj --agi 200000 --filing-type ra --year 2025

# Compare scenarios from a config file
python3 compare.py --config ../examples/scenario-config.json
```

## Project Structure

```
us-tax-analyzer/
├── skills/
│   └── tax-analyzer.md          # Claude Code skill -- document-first analysis flow
├── scripts/
│   ├── federal.py               # Federal tax brackets, QD/LTCG rates, Medicare, NIIT
│   ├── state.py                 # State income tax (37 states + DC + NYC local)
│   ├── deductions.py            # SALT cap, mortgage limits, itemized vs standard
│   └── compare.py               # Multi-scenario comparison (federal + state)
├── docs/
│   ├── filing-strategies.md     # Filing status options and when each wins
│   ├── deduction-guide.md       # Deductions by type and eligibility
│   ├── common-mistakes.md       # Frequent errors and how to catch them
│   └── state-taxes.md           # State-specific rules
├── templates/
│   ├── comparison-worksheet.md
│   └── document-checklist.md
└── examples/
    └── scenario-config.json     # Example config for compare.py
```

## Supported Filing Statuses

| Status | Code | Form |
|--------|------|------|
| Single | `single` | 1040 |
| Married Filing Jointly | `mfj` | 1040 |
| Married Filing Separately | `mfs` | 1040 or 1040-NR |
| Head of Household | `hoh` | 1040 |
| Nonresident Alien | `single`/`mfs` | 1040-NR |

## What the Scripts Calculate

### Federal (`federal.py`)
- **Federal income tax** at 2025 graduated rates (10%--37%)
- **Qualified dividends / LTCG** at preferential rates (0%/15%/20%)
- **Additional Medicare Tax** (0.9% on wages over threshold)
- **Net Investment Income Tax** (3.8% for applicable filers)

### State (`state.py`)
- **37 states + DC** covered (9 no-tax, 21 flat-rate, 7 progressive + DC)
- **NYC local income tax** (optional, on top of NY state)
- **Progressive brackets** for CA, NY, NJ, OR, MN, HI, DC

### Deductions (`deductions.py`)
- **SALT deduction** with 2025 OBBB cap ($40,000 MFJ / $20,000 MFS, phase-down for high AGI)
- **Mortgage interest** deduction with TCJA loan limits
- **Itemized vs standard** deduction comparison

### Comparison (`compare.py`)
- **Side-by-side** federal + state + total tax for multiple scenarios
- **Withholding** tracked separately (federal + state)
- **Refund/owed** per scenario with recommendation

## Limitations

- Educational estimates only -- not a substitute for professional tax advice
- Tax laws change frequently -- verify current rules before filing
- Does not handle: AMT, foreign tax credit, FBAR/FATCA, self-employment tax, rental income, K-1 partnerships, education credits phase-outs, child tax credit

## License

MIT
