"""
Federal tax bracket calculations.

All 2025 figures reflect the One Big Beautiful Bill Act (OBBB), signed July 4, 2025,
which retroactively changed brackets, standard deductions, and capital gains thresholds
for tax year 2025.

Sources:
- Tax Foundation: https://taxfoundation.org/data/all/federal/2025-tax-brackets/
- Bradford Tax Institute: https://bradfordtaxinstitute.com/Free_Resources/2025-Capital-Gains-Rates.aspx
- IRS: https://www.irs.gov/filing/federal-income-tax-rates-and-brackets

Usage:
    python3 brackets.py --income 150000 --status mfj --year 2025
    python3 brackets.py --income 250000 --status mfs --year 2025 --qualified-dividends 500
"""

import argparse
import json
import sys

# 2025 Federal Tax Brackets (post-OBBB)
BRACKETS = {
    2025: {
        "single": [
            (11_925, 0.10),
            (48_475, 0.12),
            (103_350, 0.22),
            (197_300, 0.24),
            (250_525, 0.32),
            (626_350, 0.35),
            (float("inf"), 0.37),
        ],
        "mfj": [
            (23_850, 0.10),
            (96_950, 0.12),
            (206_700, 0.22),
            (394_600, 0.24),
            (501_050, 0.32),
            (751_600, 0.35),
            (float("inf"), 0.37),
        ],
        "mfs": [
            (11_925, 0.10),
            (48_475, 0.12),
            (103_350, 0.22),
            (197_300, 0.24),
            (250_525, 0.32),
            (375_800, 0.35),
            (float("inf"), 0.37),
        ],
        "hoh": [
            (17_000, 0.10),
            (64_850, 0.12),
            (103_350, 0.22),
            (197_300, 0.24),
            (250_500, 0.32),
            (626_350, 0.35),
            (float("inf"), 0.37),
        ],
    },
}

# 2025 Qualified Dividends / Long-Term Capital Gains Brackets (post-OBBB)
QD_BRACKETS = {
    2025: {
        "single": [(48_350, 0.00), (517_200, 0.15), (float("inf"), 0.20)],
        "mfj": [(96_700, 0.00), (600_050, 0.15), (float("inf"), 0.20)],
        "mfs": [(48_350, 0.00), (300_000, 0.15), (float("inf"), 0.20)],
        "hoh": [(64_750, 0.00), (551_350, 0.15), (float("inf"), 0.20)],
    },
}

# Standard Deductions (post-OBBB)
STANDARD_DEDUCTION = {
    2025: {
        "single": 15_750,
        "mfj": 31_500,
        "mfs": 15_750,
        "hoh": 23_625,
    },
}

# Additional Medicare Tax Thresholds (not indexed for inflation)
ADDITIONAL_MEDICARE_THRESHOLD = {
    "single": 200_000,
    "mfj": 250_000,
    "mfs": 125_000,
    "hoh": 200_000,
}

# NIIT Threshold (not indexed for inflation)
NIIT_THRESHOLD = {
    "single": 200_000,
    "mfj": 250_000,
    "mfs": 125_000,
    "hoh": 200_000,
}


def calculate_bracket_tax(taxable_income, status, year=2025):
    """Calculate federal income tax using graduated brackets.

    Args:
        taxable_income: Taxable income after deductions.
        status: Filing status ('single', 'mfj', 'mfs', 'hoh').
        year: Tax year.

    Returns:
        dict with total tax, effective rate, marginal rate, and bracket breakdown.
    """
    brackets = BRACKETS[year][status]
    tax = 0.0
    breakdown = []
    prev_limit = 0

    for limit, rate in brackets:
        if taxable_income <= prev_limit:
            break
        bracket_income = min(taxable_income, limit) - prev_limit
        bracket_tax = bracket_income * rate
        tax += bracket_tax
        if bracket_income > 0:
            breakdown.append({
                "range": f"${prev_limit:,.0f} - ${min(taxable_income, limit):,.0f}",
                "rate": f"{rate:.0%}",
                "income": round(bracket_income),
                "tax": round(bracket_tax, 2),
            })
        prev_limit = limit

    marginal_rate = 0.0
    for limit, rate in brackets:
        if taxable_income <= limit:
            marginal_rate = rate
            break

    return {
        "taxable_income": round(taxable_income),
        "tax": round(tax, 2),
        "effective_rate": round(tax / taxable_income, 4) if taxable_income > 0 else 0,
        "marginal_rate": marginal_rate,
        "breakdown": breakdown,
    }


def calculate_qd_tax(qualified_dividends, taxable_income, status, year=2025):
    """Calculate tax on qualified dividends at preferential rates.

    Args:
        qualified_dividends: Amount of qualified dividends.
        taxable_income: Total taxable income (determines which QD bracket applies).
        status: Filing status.
        year: Tax year.

    Returns:
        dict with QD tax amount and rate applied.
    """
    if qualified_dividends <= 0:
        return {"tax": 0, "rate": 0}

    qd_brackets = QD_BRACKETS[year][status]
    for limit, rate in qd_brackets:
        if taxable_income <= limit:
            return {
                "tax": round(qualified_dividends * rate, 2),
                "rate": rate,
            }

    last_rate = qd_brackets[-1][1]
    return {"tax": round(qualified_dividends * last_rate, 2), "rate": last_rate}


def calculate_additional_medicare_tax(medicare_wages, status):
    """Calculate Additional Medicare Tax (0.9% on wages over threshold).

    Args:
        medicare_wages: Total Medicare wages (W-2 box 5).
        status: Filing status.

    Returns:
        dict with tax amount and excess wages.
    """
    threshold = ADDITIONAL_MEDICARE_THRESHOLD[status]
    excess = max(0, medicare_wages - threshold)
    tax = round(excess * 0.009, 2)
    return {"tax": tax, "excess": round(excess), "threshold": threshold}


def calculate_niit(net_investment_income, magi, status):
    """Calculate Net Investment Income Tax (3.8%).

    NRAs are NOT subject to NIIT. Thresholds are not indexed for inflation.

    Args:
        net_investment_income: Sum of interest, dividends, capital gains, etc.
        magi: Modified adjusted gross income.
        status: Filing status.

    Returns:
        dict with tax amount.
    """
    threshold = NIIT_THRESHOLD[status]
    excess_magi = max(0, magi - threshold)
    taxable_amount = min(net_investment_income, excess_magi)
    tax = round(taxable_amount * 0.038, 2)
    return {"tax": tax, "taxable_amount": round(taxable_amount)}


def calculate_full_tax(
    taxable_income,
    status,
    year=2025,
    qualified_dividends=0,
    medicare_wages=0,
    net_investment_income=0,
    magi=0,
    is_nra=False,
):
    """Calculate total federal tax including all components.

    Args:
        taxable_income: Income after deductions.
        status: Filing status.
        year: Tax year.
        qualified_dividends: Qualified dividend amount.
        medicare_wages: W-2 box 5 total.
        net_investment_income: For NIIT calculation.
        magi: Modified AGI for NIIT.
        is_nra: If True, skip NIIT (NRAs exempt).

    Returns:
        dict with all tax components and total.
    """
    ordinary_income = taxable_income - qualified_dividends
    ordinary_tax = calculate_bracket_tax(ordinary_income, status, year)
    qd_tax = calculate_qd_tax(qualified_dividends, taxable_income, status, year)
    medicare = calculate_additional_medicare_tax(medicare_wages, status)

    niit = {"tax": 0, "taxable_amount": 0}
    if not is_nra and net_investment_income > 0:
        niit = calculate_niit(net_investment_income, magi, status)

    total = ordinary_tax["tax"] + qd_tax["tax"] + medicare["tax"] + niit["tax"]

    return {
        "ordinary_tax": ordinary_tax,
        "qd_tax": qd_tax,
        "additional_medicare": medicare,
        "niit": niit,
        "total_tax": round(total, 2),
        "status": status,
        "year": year,
        "is_nra": is_nra,
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate federal income tax")
    parser.add_argument("--income", type=float, required=True, help="Taxable income")
    parser.add_argument(
        "--status",
        choices=["single", "mfj", "mfs", "hoh"],
        required=True,
        help="Filing status",
    )
    parser.add_argument("--year", type=int, default=2025, help="Tax year")
    parser.add_argument(
        "--qualified-dividends", type=float, default=0, help="Qualified dividends"
    )
    parser.add_argument(
        "--medicare-wages", type=float, default=0, help="Medicare wages (W-2 box 5)"
    )
    parser.add_argument(
        "--investment-income",
        type=float,
        default=0,
        help="Net investment income for NIIT",
    )
    parser.add_argument("--magi", type=float, default=0, help="MAGI for NIIT")
    parser.add_argument(
        "--nra", action="store_true", help="Nonresident alien (skip NIIT)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    args = parser.parse_args()

    result = calculate_full_tax(
        taxable_income=args.income,
        status=args.status,
        year=args.year,
        qualified_dividends=args.qualified_dividends,
        medicare_wages=args.medicare_wages,
        net_investment_income=args.investment_income,
        magi=args.magi,
        is_nra=args.nra,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'=' * 60}")
        print(f"  Federal Tax Calculation — {args.year} ({args.status.upper()})")
        if args.nra:
            print("  (Nonresident Alien)")
        print(f"{'=' * 60}")
        print(f"\n  Taxable Income: ${args.income:,.0f}")
        print(f"\n  Bracket Breakdown:")
        for b in result["ordinary_tax"]["breakdown"]:
            print(f"    {b['rate']:>4s}  {b['range']:<40s}  ${b['tax']:>10,.2f}")
        print(f"  {'':>4s}  {'Ordinary income tax':<40s}  ${result['ordinary_tax']['tax']:>10,.2f}")

        if args.qualified_dividends > 0:
            print(
                f"\n  Qualified Dividends: ${args.qualified_dividends:,.0f} "
                f"@ {result['qd_tax']['rate']:.0%} = ${result['qd_tax']['tax']:,.2f}"
            )

        if result["additional_medicare"]["tax"] > 0:
            print(
                f"\n  Additional Medicare Tax: ${result['additional_medicare']['excess']:,} "
                f"excess x 0.9% = ${result['additional_medicare']['tax']:,.2f}"
            )

        if result["niit"]["tax"] > 0:
            print(
                f"\n  NIIT: ${result['niit']['taxable_amount']:,} "
                f"x 3.8% = ${result['niit']['tax']:,.2f}"
            )

        print(f"\n  {'TOTAL FEDERAL TAX':>44s}  ${result['total_tax']:>10,.2f}")
        print(
            f"  {'Effective Rate':>44s}  "
            f"{result['total_tax'] / args.income:.2%}" if args.income > 0 else ""
        )
        print()


if __name__ == "__main__":
    main()
