# Tax Analysis Skill

Analyze US federal and state tax returns. Compare filing scenarios, review prepared returns for errors, and recommend the optimal filing strategy.

## Prerequisites

### PDF Reading

Tax documents are typically PDFs. Claude Code can read PDFs natively in most cases. If the built-in PDF reader fails, `pdftotext` (from `poppler`) is a recommended fallback:

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Verify
pdftotext -v
```

When Claude Code's built-in PDF reader fails (usually because `pdftoppm` is not found), fall back to:

```bash
pdftotext "/path/to/document.pdf" -
```

### Reading Tax Documents from a Folder

When the user provides a folder path:

1. List all files: `ls <folder>/`
2. For each PDF, try Claude Code's `Read` tool first (supports native PDF reading)
3. If `Read` fails (e.g., `pdftoppm` not found), fall back to `pdftotext` via Bash:
   ```bash
   pdftotext "<folder>/W2.pdf" - 2>&1 | head -200
   ```
4. For multi-page PDFs (1099 consolidated forms), extract all pages:
   ```bash
   pdftotext "<folder>/1099.pdf" -
   ```
5. **W-2 PDFs are notoriously hard to parse** — they often have 4-up layouts (Federal/State/Local/Employee copies) where text extraction jumbles fields. Always:
   - Cross-reference extracted values against the user's stated numbers
   - Ask the user to confirm ambiguous values (especially boxes 3-6 for SS/Medicare)
   - Check that box 1 + box 12 codes (D/E/AA/DD) make sense

### Web Search for Latest Tax Rules

Tax laws change frequently. Before calculating, search the web for the current year's:
- Federal tax brackets (may have changed mid-year, e.g., OBBB retroactive changes)
- Standard deduction amounts
- SALT cap and phase-down thresholds
- Capital gains brackets
- Credit amounts and phase-outs

Use `WebSearch` with queries like: `"2025 federal tax brackets OBBB"`, `"2025 SALT cap phase-down"`, `"2025 standard deduction amounts"`.

## Phase 1: Gather Information

Ask the user these questions. Skip sections that don't apply.

### Filing Situation
1. What is your filing status? (Single, Married Filing Jointly, Married Filing Separately, Head of Household, Qualifying Surviving Spouse)
2. If married, what date did you marry? Does your spouse also file?
3. Do you have dependents? (number, ages, relationship)
4. What state do you live in?
5. Are you a US citizen, green card holder, or visa holder? If visa, what type and any status changes during the year?
6. Did you file a US tax return last year? What form and result (refund/owed amount)?
7. Did you receive a state tax refund from last year? (May be taxable if you itemized)

### Tax Documents
8. Where are your tax documents? Provide a folder path.
   - Read all documents: W-2, 1099 (B, DIV, INT, MISC, NEC, K), 1042-S, 1098, 1098-T, property tax receipts, vehicle registration, closing statements
   - Extract key values from each document
   - Present a summary table and ask the user to confirm accuracy
   - Flag inconsistencies (e.g., blank W-2 fields that should have values, or vice versa)

### Income Sources
9. Employment income (W-2) — how many employers?
10. Investment income — brokerage accounts, dividends, interest, capital gains?
11. Self-employment or freelance income?
12. Rental income?
13. Retirement distributions?
14. Any other income (gambling, prizes, crypto, foreign income)?

### Deductions & Credits
15. Do you own a home? Mortgage interest (1098)? Property tax?
16. Vehicle registration paid? (Some states have deductible portions)
17. Charitable contributions?
18. Student loan interest? Education expenses (1098-T)?
19. Medical expenses exceeding 7.5% of AGI?
20. Any estimated tax payments made during the year?

## Phase 2: Determine Filing Options

Based on the gathered info, identify which filing scenarios are available:

### For US Citizens / Green Card Holders
- Single, MFJ, MFS, HOH — based on marital status and dependents
- Compare MFJ vs MFS if married (MFJ usually wins, but not always)

### For Visa Holders
- Determine residency via Substantial Presence Test (SPT)
- Check exempt individual rules (F-1/J-1 first 5 calendar years)
- If NRA: 1040-NR options (Single or MFS)
- If NRA but married: evaluate §6013(g) election (elect RA, requires MFJ)
- Compare NRA MFS vs RA MFJ — mortgage interest is the key driver

### Key Decision Points
- Homeowner with mortgage → itemize likely wins; if NRA, RA election may be better
- High-income in high-tax state → SALT cap matters; check phase-down
- Investment income → NIIT (3.8%) applies to RA filers above threshold
- Treaty benefits → only available on 1040-NR; weigh against RA deductions

## Phase 3: Calculate Each Scenario

Run Python scripts for each viable scenario.

### Income Calculation
- Sum all income sources
- Apply above-the-line adjustments (IRA, student loan interest, SE tax deduction)
- Determine AGI

### Deduction Calculation
Run `scripts/deductions.py`:
- SALT: state income tax + property tax + vehicle fees + SDI, subject to cap
- Mortgage interest: check loan limit (post-TCJA $750K MFJ, $375K MFS)
- Compare itemized vs standard deduction
- NRA special rules: no mortgage interest, no standard deduction

### Tax Calculation
Run `scripts/brackets.py`:
- Federal tax at graduated rates
- Qualified dividends / LTCG at preferential rates (0%/15%/20%)
- Additional Medicare Tax (0.9% on wages over threshold)
- NIIT (3.8% on investment income for applicable filers)
- For NRAs: FDAP income at flat 30% or treaty rates on Schedule NEC

## Phase 4: Compare Scenarios

Present a side-by-side comparison table showing:
- Income, deductions, taxable income
- Each tax component
- Total tax, withholding, result (refund/owed)

Identify the winning scenario and explain why — break down which factors drive the difference (mortgage deduction, SALT, treaty benefits, credits, etc.).

## Phase 5: Review Prepared Returns (Optional)

If the user provides accountant-prepared returns, compare against calculated values.

### Common Errors to Check
1. **Suboptimal filing status** — didn't evaluate all available options
2. **Wrong SALT cap** — using outdated limits
3. **Missing deductions** — mortgage interest, property tax, SDI, vehicle fees
4. **Incorrect withholding data** — W-2 values don't match what's on the return
5. **Income classification errors** — NRA investment income as ECI instead of FDAP
6. **Phantom tax data** — Form 8959 with incorrect Medicare wages
7. **Missing credits** — education, child tax, retirement savings
8. **Prior-year amounts wrong** — state refunds, carryforwards
9. **Calculation errors** — verify tax computation against brackets

### For Each Issue Found
- What the return shows vs what it should be
- Dollar impact
- Severity (Critical / High / Medium / Low)

## Phase 6: Recommendation

1. Which filing strategy to use and why
2. Estimated total tax and refund/amount owed
3. Dollar savings vs alternatives
4. Action items (file, amend, contact accountant)
5. Areas where professional advice is recommended

Always end with:
> **Disclaimer**: This analysis is for educational purposes only and does not constitute tax advice. Consult a qualified tax professional (CPA or Enrolled Agent) before filing.

## Script Reference

```bash
# Federal tax calculation
python3 scripts/brackets.py --income <amount> --status <single|mfj|mfs|hoh> [--qualified-dividends <amount>] [--medicare-wages <amount>] [--nra]

# Deduction calculation
python3 scripts/deductions.py --state-tax <amount> --property-tax <amount> --mortgage-interest <amount> --status <status> --agi <amount> --filing-type <ra|nra>

# Scenario comparison
python3 scripts/compare.py --config <file.json>
```
