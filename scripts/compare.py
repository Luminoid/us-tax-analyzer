"""
Multi-scenario tax comparison.

Supports:
- Individual scenarios (single filer)
- Combined scenarios (e.g., two NRA spouses filing separately, compared against MFJ)
- State itemized deductions separate from federal (CA allows mortgage/property tax even for NRAs)
- State treaty addback (CA doesn't honor most federal treaty exemptions)
- State income adjustments (e.g., exclude own-state refund from state taxable income)

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
    state_itemized_deductions=None,
    state_income_adjustment=0,
    state_treaty_addback=0,
    **kwargs,
):
    """Build a complete tax scenario with all calculations.

    Args:
        name: Scenario label (e.g., "MFJ Itemized").
        status: Filing status ('single', 'mfj', 'mfs', 'hoh').
        is_nra: Nonresident alien flag.
        wages: W-2 wages (box 1).
        treaty_exemption: Treaty-exempt income amount (federal only).
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
        state_withholding: State tax withheld.
        state_code: Two-letter state code (e.g., 'CA').
        nyc_resident: NYC local tax flag.
        year: Tax year.
        state_itemized_deductions: Override state deductions (dict with
            mortgage_interest, property_tax, car_vlf, other). If provided,
            uses these instead of state standard deduction. Useful when
            state allows deductions that federal NRA rules disallow (e.g.,
            CA allows mortgage interest for federal NRAs).
        state_income_adjustment: Amount to subtract from state AGI (e.g.,
            own-state refund that's taxable federally but not on state return).
        state_treaty_addback: Amount to add back to state AGI when state
            doesn't honor federal treaty exemptions (e.g., CA doesn't honor
            Article 20 $5,000 exemption).

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
    state_taxable = 0
    if state_code:
        state_agi = agi + state_treaty_addback - state_income_adjustment

        if state_itemized_deductions is not None:
            sid = state_itemized_deductions
            state_itemized_total = (
                sid.get("mortgage_interest", 0)
                + sid.get("property_tax", 0)
                + sid.get("car_vlf", 0)
                + sid.get("other", 0)
            )
            state_std = get_state_standard_deduction(state_code, status)
            state_deduction = max(state_itemized_total, state_std)
        else:
            state_deduction = get_state_standard_deduction(state_code, status)

        state_taxable = max(0, state_agi - state_deduction)
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
        "state_taxable": round(state_taxable),
        "state_tax_amount": round(state_tax_amount),
        "state_treaty_addback": round(state_treaty_addback),
        "state_income_adjustment": round(state_income_adjustment),
        "total_tax": round(total_tax),
        "withholding": round(withholding),
        "state_withholding": round(state_withholding),
        "total_withholding": round(total_withholding),
        "result": round(result),
        "result_label": "REFUND" if result >= 0 else "OWED",
    }


def _combine_scenarios(scenarios, combined_name):
    """Combine multiple scenarios into a single aggregated result.

    Used to compare "Spouse A NRA + Spouse B NRA" against "MFJ" as a single
    line item. Sums all tax, withholding, and result fields.

    Args:
        scenarios: List of scenario result dicts to combine.
        combined_name: Display name for the combined result.

    Returns:
        dict with combined totals (subset of fields for comparison).
    """
    combined = {
        "name": combined_name,
        "is_combined": True,
        "components": [s["name"] for s in scenarios],
        "status": " + ".join(s["status"].upper() for s in scenarios),
        "is_nra": any(s["is_nra"] for s in scenarios),
        "year": scenarios[0]["year"],
        "state_code": scenarios[0].get("state_code", ""),
        "income": {
            "wages": sum(s["income"]["wages"] for s in scenarios),
            "treaty_exemption": sum(s["income"]["treaty_exemption"] for s in scenarios),
            "interest": sum(s["income"]["interest"] for s in scenarios),
            "dividends": sum(s["income"]["dividends"] for s in scenarios),
            "qualified_dividends": sum(s["income"]["qualified_dividends"] for s in scenarios),
            "short_term_gains": sum(s["income"]["short_term_gains"] for s in scenarios),
            "long_term_gains": sum(s["income"]["long_term_gains"] for s in scenarios),
            "other_income": sum(s["income"]["other_income"] for s in scenarios),
            "agi": sum(s["income"]["agi"] for s in scenarios),
        },
        "deductions": {
            "salt": {
                "allowed_deduction": sum(
                    s["deductions"]["salt"]["allowed_deduction"] for s in scenarios
                ),
            },
            "mortgage": {
                "deductible": sum(
                    s["deductions"]["mortgage"]["deductible"] for s in scenarios
                ),
            },
        },
        "deduction_comparison": {
            "recommended": "COMBINED",
            "deduction": sum(s["deduction_comparison"]["deduction"] for s in scenarios),
        },
        "taxable_income": sum(s["taxable_income"] for s in scenarios),
        "tax": {
            "ordinary_tax": {
                "tax": sum(s["tax"]["ordinary_tax"]["tax"] for s in scenarios),
            },
            "qd_tax": {
                "tax": sum(s["tax"]["qd_tax"]["tax"] for s in scenarios),
            },
            "additional_medicare": {
                "tax": sum(s["tax"]["additional_medicare"]["tax"] for s in scenarios),
            },
            "niit": {
                "tax": sum(s["tax"]["niit"]["tax"] for s in scenarios),
            },
        },
        "fdap_tax": sum(s["fdap_tax"] for s in scenarios),
        "federal_tax": sum(s["federal_tax"] for s in scenarios),
        "state_tax": None,
        "state_tax_amount": sum(s["state_tax_amount"] for s in scenarios),
        "total_tax": sum(s["total_tax"] for s in scenarios),
        "withholding": sum(s["withholding"] for s in scenarios),
        "state_withholding": sum(s["state_withholding"] for s in scenarios),
        "total_withholding": sum(s["total_withholding"] for s in scenarios),
    }
    combined["result"] = combined["total_withholding"] - combined["total_tax"]
    combined["result_label"] = "REFUND" if combined["result"] >= 0 else "OWED"
    return combined


def compare_scenarios(display_scenarios):
    """Compare multiple tax scenarios side by side.

    Args:
        display_scenarios: List of scenario dicts (individual or combined).

    Returns:
        dict with comparison results including best/worst/savings.
    """
    best = min(display_scenarios, key=lambda s: s["total_tax"])
    worst = max(display_scenarios, key=lambda s: s["total_tax"])
    return {
        "scenarios": display_scenarios,
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
    if any(not s.get("is_combined") and not s["is_nra"] and s["tax"]["niit"]["tax"] for s in scenarios):
        row("NIIT", lambda s: s["tax"]["niit"]["tax"] if not s["is_nra"] or s.get("is_combined") else "N/A")
    elif any(s.get("is_combined") or (not s["is_nra"] and s["tax"]["niit"]["tax"]) for s in scenarios):
        row("NIIT", lambda s: s["tax"]["niit"]["tax"] if not s["is_nra"] else "N/A")
    if any(s["fdap_tax"] for s in scenarios):
        row("FDAP/NEC tax", lambda s: s["fdap_tax"] if s["fdap_tax"] else "N/A")
    row("Federal total", lambda s: s["federal_tax"])

    if any(s["state_tax_amount"] for s in scenarios):
        print("\nSTATE TAX")
        row("State", lambda s: s["state_code"].upper() if s.get("state_code") else "N/A")
        row("State tax", lambda s: s["state_tax_amount"])
        if any(s.get("state_tax") and s["state_tax"].get("local_tax", 0) for s in scenarios):
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

    # Build all individual scenarios
    all_scenarios = [build_scenario(**s) for s in config["scenarios"]]

    # Process combined groups and standalone scenarios for display
    display_scenarios = []
    combined_groups = config.get("combined", [])
    grouped_names = set()
    for group in combined_groups:
        members = [s for s in all_scenarios if s["name"] in group["members"]]
        if len(members) == len(group["members"]):
            combined = _combine_scenarios(members, group["name"])
            display_scenarios.append(combined)
            grouped_names.update(group["members"])

    # Add standalone scenarios (not part of any combined group)
    for s in all_scenarios:
        if s["name"] not in grouped_names:
            display_scenarios.append(s)

    comparison = compare_scenarios(display_scenarios)

    if args.json:
        print(json.dumps(comparison, indent=2, default=str))
    else:
        print_comparison(comparison)


if __name__ == "__main__":
    main()
