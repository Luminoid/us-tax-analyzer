"""
Multi-scenario tax comparison.

Usage:
    python3 compare.py --config scenarios.json
    python3 compare.py --config scenarios.json --json
"""

import argparse
import json
import sys

from federal import calculate_full_tax
from deductions import calculate_itemized_deductions, compare_standard_vs_itemized
from state import calculate_state_tax, get_state_standard_deduction


def build_scenario(
    name,
    status,
    is_nra=False,
    wages=0,
    treaty_exemption=0,
    interest=0,
    dividends=0,
    qualified_dividends=0,
    short_term_gains=0,
    long_term_gains=0,
    other_income=0,
    state_income_tax=0,
    property_tax=0,
    car_vlf=0,
    sdi=0,
    mortgage_interest=0,
    loan_balance=0,
    loan_origination_date="2024-01-01",
    charitable=0,
    medicare_wages=0,
    fdap_tax=0,
    withholding=0,
    state_withholding=0,
    state_code="",
    nyc_resident=False,
    year=2025,
    **kwargs,
):
    """Build a complete tax scenario with all calculations.

    Args:
        name: Scenario label (e.g., "MFJ Itemized").
        status: Filing status ('single', 'mfj', 'mfs', 'hoh').
        is_nra: Nonresident alien flag.
        wages: W-2 wages (box 1).
        treaty_exemption: Treaty-exempt income amount.
        interest: Interest income.
        dividends: Ordinary dividends (total).
        qualified_dividends: Qualified portion of dividends.
        short_term_gains: Short-term capital gains.
        long_term_gains: Long-term capital gains.
        other_income: Any other taxable income (state refunds, etc.).
        state_income_tax: State income tax withheld.
        property_tax: Real estate tax paid.
        car_vlf: Vehicle license fee.
        sdi: State disability insurance.
        mortgage_interest: From 1098.
        loan_balance: Outstanding principal for mortgage limit.
        loan_origination_date: For TCJA threshold.
        charitable: Charitable contributions.
        medicare_wages: W-2 box 5 (for Additional Medicare Tax).
        fdap_tax: NRA flat tax on FDAP income (Schedule NEC total).
        withholding: Total federal tax withheld.
        year: Tax year.

    Returns:
        dict with complete scenario results.
    """
    taxable_wages = wages - treaty_exemption if is_nra else wages
    total_income = (
        taxable_wages + interest + dividends + short_term_gains
        + long_term_gains + other_income
    )
    agi = total_income

    deductions = calculate_itemized_deductions(
        state_income_tax=state_income_tax,
        property_tax=property_tax,
        car_vlf=car_vlf,
        sdi=sdi,
        mortgage_interest=mortgage_interest,
        loan_balance=loan_balance,
        loan_origination_date=loan_origination_date,
        charitable=charitable,
        agi=agi,
        status=status,
        is_nra=is_nra,
        year=year,
    )

    comparison = compare_standard_vs_itemized(
        deductions["total_itemized"], status, year, is_nra
    )

    taxable_income = max(0, agi - comparison["deduction"])
    net_investment_income = interest + dividends + short_term_gains + long_term_gains

    tax_result = calculate_full_tax(
        taxable_income=taxable_income,
        status=status,
        year=year,
        qualified_dividends=min(qualified_dividends, taxable_income),
        medicare_wages=medicare_wages,
        net_investment_income=net_investment_income,
        magi=agi,
        is_nra=is_nra,
    )

    federal_tax = tax_result["total_tax"] + fdap_tax

    # State tax calculation
    state_result = None
    state_tax_amount = 0
    if state_code:
        state_std = get_state_standard_deduction(state_code, status)
        state_taxable = max(0, agi - state_std) if state_std > 0 else max(0, agi)
        state_result = calculate_state_tax(
            state=state_code,
            taxable_income=state_taxable,
            status=status,
            year=year,
            nyc_resident=nyc_resident,
        )
        state_tax_amount = state_result["total_tax"]

    total_tax = federal_tax + state_tax_amount
    total_withholding = withholding + state_withholding
    result = total_withholding - total_tax

    return {
        "name": name,
        "status": status,
        "is_nra": is_nra,
        "year": year,
        "state_code": state_code,
        "income": {
            "wages": round(wages),
            "treaty_exemption": round(treaty_exemption),
            "interest": round(interest),
            "dividends": round(dividends),
            "qualified_dividends": round(qualified_dividends),
            "short_term_gains": round(short_term_gains),
            "long_term_gains": round(long_term_gains),
            "other_income": round(other_income),
            "agi": round(agi),
        },
        "deductions": deductions,
        "deduction_comparison": comparison,
        "taxable_income": round(taxable_income),
        "tax": tax_result,
        "fdap_tax": round(fdap_tax),
        "federal_tax": round(federal_tax),
        "state_tax": state_result,
        "state_tax_amount": round(state_tax_amount),
        "total_tax": round(total_tax),
        "withholding": round(withholding),
        "state_withholding": round(state_withholding),
        "total_withholding": round(total_withholding),
        "result": round(result),
        "result_label": "REFUND" if result >= 0 else "OWED",
    }


def compare_scenarios(scenarios):
    """Compare multiple tax scenarios side by side."""
    best = min(scenarios, key=lambda s: s["total_tax"])
    worst = max(scenarios, key=lambda s: s["total_tax"])
    return {
        "scenarios": scenarios,
        "best": {
            "name": best["name"],
            "total_tax": best["total_tax"],
            "result": best["result"],
            "result_label": best["result_label"],
        },
        "worst": {
            "name": worst["name"],
            "total_tax": worst["total_tax"],
            "result": worst["result"],
            "result_label": worst["result_label"],
        },
        "savings": worst["total_tax"] - best["total_tax"],
    }


def print_comparison(comparison):
    """Print a formatted comparison table."""
    scenarios = comparison["scenarios"]
    col_width = max(20, 80 // (len(scenarios) + 1))

    print(f"\n{'=' * (30 + col_width * len(scenarios))}")
    print("  TAX SCENARIO COMPARISON")
    print(f"{'=' * (30 + col_width * len(scenarios))}")

    header = f"{'Item':<30s}"
    for s in scenarios:
        header += f"{s['name']:>{col_width}s}"
    print(f"\n{header}")
    print("-" * (30 + col_width * len(scenarios)))

    def row(label, key_fn):
        line = f"  {label:<28s}"
        for s in scenarios:
            val = key_fn(s)
            if val == "N/A":
                line += f"{'N/A':>{col_width}s}"
            elif isinstance(val, str):
                line += f"{val:>{col_width}s}"
            else:
                line += f"{'$' + f'{val:,.0f}':>{col_width}s}"
        print(line)

    print("\nINCOME")
    row("Wages", lambda s: s["income"]["wages"])
    if any(s["income"]["treaty_exemption"] for s in scenarios):
        row("Treaty exemption", lambda s: -s["income"]["treaty_exemption"] if s["income"]["treaty_exemption"] else "N/A")
    if any(s["income"]["interest"] for s in scenarios):
        row("Interest", lambda s: s["income"]["interest"])
    if any(s["income"]["dividends"] for s in scenarios):
        row("Dividends", lambda s: s["income"]["dividends"])
    if any(s["income"]["short_term_gains"] for s in scenarios):
        row("ST Capital gains", lambda s: s["income"]["short_term_gains"])
    if any(s["income"]["long_term_gains"] for s in scenarios):
        row("LT Capital gains", lambda s: s["income"]["long_term_gains"])
    if any(s["income"]["other_income"] for s in scenarios):
        row("Other income", lambda s: s["income"]["other_income"])
    row("AGI", lambda s: s["income"]["agi"])

    print("\nDEDUCTIONS")
    row("SALT allowed", lambda s: s["deductions"]["salt"]["allowed_deduction"])
    row("Mortgage interest", lambda s: s["deductions"]["mortgage"]["deductible"])
    row("Deduction type", lambda s: s["deduction_comparison"]["recommended"].upper())
    row("Total deduction", lambda s: s["deduction_comparison"]["deduction"])

    print("\nFEDERAL TAX")
    row("Taxable income", lambda s: s["taxable_income"])
    row("Income tax", lambda s: s["tax"]["ordinary_tax"]["tax"] + s["tax"]["qd_tax"]["tax"])
    if any(s["tax"]["additional_medicare"]["tax"] for s in scenarios):
        row("Addl Medicare", lambda s: s["tax"]["additional_medicare"]["tax"])
    if any(not s["is_nra"] and s["tax"]["niit"]["tax"] for s in scenarios):
        row("NIIT", lambda s: s["tax"]["niit"]["tax"] if not s["is_nra"] else "N/A")
    if any(s["fdap_tax"] for s in scenarios):
        row("FDAP/NEC tax", lambda s: s["fdap_tax"] if s["is_nra"] else "N/A")
    row("Federal total", lambda s: s["federal_tax"])

    if any(s["state_tax_amount"] for s in scenarios):
        print("\nSTATE TAX")
        row("State", lambda s: s["state_code"].upper() if s["state_code"] else "N/A")
        row("State tax", lambda s: s["state_tax_amount"])
        if any(s.get("state_tax", {}).get("local_tax", 0) for s in scenarios):
            row("Local tax", lambda s: s["state_tax"]["local_tax"] if s.get("state_tax") else 0)

    print(f"\n{'-' * (30 + col_width * len(scenarios))}")
    row("TOTAL TAX", lambda s: s["total_tax"])
    row("Federal withheld", lambda s: s["withholding"])
    if any(s["state_withholding"] for s in scenarios):
        row("State withheld", lambda s: s["state_withholding"])
    row("Total withheld", lambda s: s["total_withholding"])

    line = f"  {'RESULT':<28s}"
    for s in scenarios:
        val = abs(s["result"])
        label = s["result_label"]
        line += f"{'$' + f'{val:,.0f}' + ' ' + label:>{col_width}s}"
    print(line)

    best = comparison["best"]
    print(f"\n  RECOMMENDED: {best['name']}")
    print(f"  Savings vs worst: ${comparison['savings']:,.0f}\n")


def main():
    parser = argparse.ArgumentParser(description="Compare tax filing scenarios")
    parser.add_argument("--config", required=True, help="JSON config file with scenario definitions")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    scenarios = [build_scenario(**s) for s in config["scenarios"]]
    comparison = compare_scenarios(scenarios)

    if args.json:
        print(json.dumps(comparison, indent=2, default=str))
    else:
        print_comparison(comparison)


if __name__ == "__main__":
    main()
