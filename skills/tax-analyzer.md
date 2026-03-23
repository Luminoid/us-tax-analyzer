# Tax Analyzer Skill

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

### Web Search for Latest Tax Rules

Tax laws change frequently. Before calculating, search the web for the current year's:
- Federal tax brackets (may have changed mid-year, e.g., OBBB retroactive changes)
- Standard deduction amounts
- SALT cap and phase-down thresholds
- Capital gains brackets
- Credit amounts and phase-outs

Use `WebSearch` with queries like: `"2025 federal tax brackets OBBB"`, `"2025 SALT cap phase-down"`, `"2025 standard deduction amounts"`.

## Phase 1: Gather Information (Document-First)

Read documents first, extract as much as possible automatically, then only ask what's missing.

### Step 1: Ask for document folder and key context

Ask these upfront (cannot be extracted from documents):

1. **Where are your tax documents?** Provide a folder path.
2. **What is your marital status?** If married, when did you marry? Does your spouse also file a US return?
3. **Are you a US citizen, green card holder, or visa holder?** If visa, what type and any status changes during the year?
4. **Do you have dependents?** (number, ages, relationship)

### Step 2: Read all documents in the folder

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
   - Cross-reference extracted values against each other for consistency
   - Flag ambiguous values (especially boxes 3-6 for SS/Medicare)
   - Check that box 1 + box 12 codes (D/E/AA/DD) make sense

### Step 3: Auto-extract answers from documents

Extract and organize the following from the documents read:

| Data Point | Source Document | Fields to Extract |
|-----------|----------------|-------------------|
| State of residence | W-2 box 15 | State code |
| Number of employers | Count of W-2s | -- |
| Wages | W-2 box 1 | Per employer + total |
| Federal withholding | W-2 box 2 | Per employer + total |
| State withholding | W-2 box 17 | Per employer + total |
| Medicare wages | W-2 box 5 | Per employer + total |
| SS/Medicare exempt? | W-2 boxes 3-6 | Blank = exempt (F-1/J-1) |
| Interest income | 1099-INT box 1 | Per account + total |
| Dividends | 1099-DIV box 1a, 1b | Ordinary + qualified |
| Capital gains/losses | 1099-B | Short-term + long-term totals |
| NRA treaty income | 1042-S | Income code, rate, amount withheld |
| Mortgage interest | 1098 box 1 | Per servicer + total |
| Loan balance | 1098 box 2 | Outstanding principal |
| Loan origination date | 1098 box 3 | For TCJA limit determination |
| Property tax | Receipts / closing stmt | Total paid in calendar year |
| Vehicle license fee | Registration receipt | Deductible VLF portion |
| Student loan interest | 1098-E | Amount paid |
| Education expenses | 1098-T box 1, 5 | Payments - scholarships |
| Prior year return | Prior 1040/1040-NR | Form used, refund/owed amount |
| Prior state refund | Prior return / 1099-G | Amount (taxable if itemized) |
| Estimated payments | Payment receipts | Quarterly amounts |

### Step 4: Present extracted summary and ask for confirmation

Present a summary table of everything extracted. Example format:

```
EXTRACTED FROM YOUR DOCUMENTS:

Income:
  Wages (W-2, Employer A):        $120,000
  Wages (W-2, Employer B):         $30,000
  Interest (1099-INT, Bank X):        $500
  Dividends (1099-DIV, Broker Y):   $1,200  (qualified: $900)
  Capital gains (1099-B):           $3,500  (ST: $1,000, LT: $2,500)

Withholding:
  Federal (W-2 total):             $28,000
  State (W-2 total):                $8,500

Deductions:
  Mortgage interest (1098):        $22,000  (loan: $450K, originated 2021)
  Property tax (receipts):          $7,200
  Vehicle license fee:                $280

State: California (from W-2)
Filing status: [NEED TO CONFIRM]
Dependents: [NEED TO CONFIRM]

Please confirm these values are correct, and let me know:
- Your filing status (Single / MFJ / MFS / HOH)
- Any income sources NOT listed above (freelance, rental, crypto, foreign, etc.)
- Charitable contributions (no standard form -- need your total)
- Medical expenses if significant (>7.5% of AGI)
- Any other deductions or credits
```

### Step 5: Ask only remaining questions

Based on what could NOT be extracted, ask targeted follow-up questions. Common ones:

- **Filing status** -- if not determinable from documents (married? prior return may hint)
- **Marriage date** -- if married, when? Does spouse also file?
- **Charitable contributions** -- no standard form to extract from
- **Medical expenses** -- only if potentially exceeding 7.5% AGI threshold
- **Self-employment income** -- if no 1099-NEC found but user might have unreported
- **Foreign income** -- if visa holder or documents suggest foreign accounts
- **Prior year state refund** -- if user itemized last year (may be taxable)
- **Last year's filing** -- form used (1040 vs 1040-NR) and result, if no prior return provided

Skip questions where the answer is clearly "no" based on the documents (e.g., don't ask about rental income if there are no Schedule E or 1099-MISC forms).

## Phase 2: Determine Filing Options

Based on the gathered info, identify which filing scenarios are available:

### For US Citizens / Green Card Holders
- Single, MFJ, MFS, HOH -- based on marital status and dependents
- Compare MFJ vs MFS if married (MFJ usually wins, but not always)

### For Visa Holders
- Determine residency via Substantial Presence Test (SPT)
- Check exempt individual rules (F-1/J-1 first 5 calendar years)
- If NRA: 1040-NR options (Single or MFS)
- If NRA but married: evaluate section 6013(g) election (elect RA, requires MFJ)
- Compare NRA MFS vs RA MFJ -- mortgage interest is the key driver

### Key Decision Points
- Homeowner with mortgage -> itemize likely wins; if NRA, RA election may be better
- High-income in high-tax state -> SALT cap matters; check phase-down
- Investment income -> NIIT (3.8%) applies to RA filers above threshold
- Treaty benefits -> only available on 1040-NR; weigh against RA deductions

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

### Federal Tax Calculation
Run `scripts/federal.py`:
- Federal tax at graduated rates
- Qualified dividends / LTCG at preferential rates (0%/15%/20%)
- Additional Medicare Tax (0.9% on wages over threshold)
- NIIT (3.8% on investment income for applicable filers)
- For NRAs: FDAP income at flat 30% or treaty rates on Schedule NEC

### State Tax Calculation
Run `scripts/state.py`:
- 37 states + DC covered (9 no-tax, 21 flat-rate, 7 progressive + DC)
- NYC local income tax (if applicable)
- State standard deductions where applicable (CA, NY, OR)

## Phase 4: Compare Scenarios

Present a side-by-side comparison table showing:
- Income, deductions, taxable income
- Federal tax components
- State tax (and local if applicable)
- Total tax (federal + state), total withholding (federal + state), net result (refund/owed)

Identify the winning scenario and explain why -- break down which factors drive the difference (mortgage deduction, SALT, treaty benefits, credits, etc.).

## Phase 5: Review Prepared Returns (Optional)

If the user provides accountant-prepared returns, compare against calculated values.

### Common Errors to Check
1. **Suboptimal filing status** -- didn't evaluate all available options
2. **Wrong SALT cap** -- using outdated limits
3. **Missing deductions** -- mortgage interest, property tax, SDI, vehicle fees
4. **Incorrect withholding data** -- W-2 values don't match what's on the return
5. **Income classification errors** -- NRA investment income as ECI instead of FDAP
6. **Phantom tax data** -- Form 8959 with incorrect Medicare wages
7. **Missing credits** -- education, child tax, retirement savings
8. **Prior-year amounts wrong** -- state refunds, carryforwards
9. **Calculation errors** -- verify tax computation against brackets

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
python3 scripts/federal.py --income <amount> --status <single|mfj|mfs|hoh> [--qualified-dividends <amount>] [--medicare-wages <amount>] [--nra]

# State tax calculation
python3 scripts/state.py --state <XX> --income <amount> --status <single|mfj|mfs|hoh> [--nyc]

# Deduction calculation
python3 scripts/deductions.py --state-tax <amount> --property-tax <amount> --mortgage-interest <amount> --status <status> --agi <amount> --filing-type <ra|nra>

# Scenario comparison (federal + state)
python3 scripts/compare.py --config <file.json>
```
