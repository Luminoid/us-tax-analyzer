# US Tax Advisor

A Claude Code skill + Python toolkit for US federal and state income tax analysis. Compares filing scenarios, calculates deductions, and reviews returns for errors.

## What It Does

1. **Gathers your tax info** — filing status, income sources, deductions, documents
2. **Reads tax documents** (W-2, 1099, 1098, 1042-S) from a folder you provide
3. **Calculates tax** under multiple filing scenarios
4. **Compares scenarios** side-by-side with a clear recommendation
5. **Reviews prepared returns** — flags errors, missing deductions, and suboptimal strategies

## Prerequisites

- **Python 3.10+** (no external dependencies — stdlib only)
- **poppler** (recommended — fallback for reading tax document PDFs if Claude Code's native PDF reader fails)

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
git clone https://github.com/anthropics/us-tax-advisor.git

# Copy skill to your project
mkdir -p your-project/.claude/skills/
cp us-tax-advisor/skills/tax-analysis.md your-project/.claude/skills/
```

Then in Claude Code, invoke: `/tax-analysis`

The skill will:
1. Ask you questions about your filing situation
2. Read your tax documents from a folder you specify
3. Search the web for the latest tax rules
4. Run the Python scripts to calculate and compare scenarios
5. Present a recommendation

### Option 2: Python Scripts (Standalone)

```bash
# Clone and use directly
git clone https://github.com/anthropics/us-tax-advisor.git
cd us-tax-advisor/scripts

# Calculate federal tax
python3 brackets.py --income 150000 --status mfj --year 2025

# Calculate deductions
python3 deductions.py --state-tax 12000 --property-tax 8000 \
    --mortgage-interest 25000 --status mfj --agi 200000 --filing-type ra --year 2025

# Compare scenarios from a config file
python3 scripts/compare.py --config my_scenarios.json --json
```

## Project Structure

```
us-tax-advisor/
├── skills/
│   └── tax-analysis.md        # Claude Code skill — interactive analysis flow
├── scripts/
│   ├── brackets.py            # Federal tax brackets, QD/LTCG rates, Medicare, NIIT
│   ├── deductions.py          # SALT cap, mortgage limits, itemized vs standard
│   └── compare.py             # Multi-scenario comparison engine
├── docs/
│   ├── filing-strategies.md   # Filing status options and when each wins
│   ├── deduction-guide.md     # Deductions by type and eligibility
│   ├── common-mistakes.md     # Frequent errors and how to catch them
│   └── state-taxes.md         # State-specific rules
├── templates/
│   ├── comparison-worksheet.md
│   └── document-checklist.md
└── examples/
    └── scenario-config.json   # Example config for compare.py
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

- **Federal income tax** at 2025 graduated rates (10%–37%)
- **Qualified dividends / LTCG** at preferential rates (0%/15%/20%)
- **SALT deduction** with 2025 OBBB cap ($40,000 MFJ / $20,000 MFS, phase-down for high AGI, floor $10K/$5K MFS)
- **Mortgage interest** deduction with TCJA loan limits
- **Itemized vs standard** deduction comparison
- **Additional Medicare Tax** (0.9% on wages over threshold)
- **Net Investment Income Tax** (3.8% for applicable filers)

## Limitations

- Educational estimates only — not a substitute for professional tax advice
- Tax laws change frequently — verify current rules before filing
- Does not handle: AMT, foreign tax credit, FBAR/FATCA, self-employment tax, rental income, K-1 partnerships, education credits phase-outs, child tax credit

## License

MIT
