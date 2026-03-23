"""
State income tax calculations.

Covers:
- No-income-tax states (9 states)
- Flat-rate states (21 states)
- Progressive-rate states (CA, NY, NJ, OR, MN, HI, VT, DC, and others)
- NYC local income tax

All 2025 figures. Sources:
- Tax Foundation: https://taxfoundation.org/data/all/state/state-income-tax-rates-2025/

Usage:
    python3 state.py --state CA --income 150000 --status mfj --year 2025
    python3 state.py --state TX --income 150000 --status single
"""

import argparse
import json

# States with no income tax
NO_TAX_STATES = {"AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY"}

# Flat-rate states (2025)
FLAT_RATE = {
    "AZ": 0.025,
    "CO": 0.044,
    "GA": 0.0549,
    "ID": 0.058,
    "IL": 0.0495,
    "IN": 0.0305,
    "IA": 0.0380,
    "KY": 0.04,
    "MI": 0.0425,
    "MS": 0.047,
    "MO": 0.048,
    "MT": 0.059,
    "NC": 0.045,
    "ND": 0.0195,
    "OH": 0.035,  # Effective flat after low-income exemption
    "OK": 0.0475,
    "PA": 0.0307,
    "UT": 0.0465,
    "VA": 0.0575,  # Top marginal; simplified as flat for high earners
    "WV": 0.0512,
    "WI": 0.0530,  # Top marginal; simplified as flat for high earners
}

# Progressive-rate states (2025 brackets)
# Format: list of (upper_limit, rate) tuples per status
PROGRESSIVE_BRACKETS = {
    "CA": {
        "single": [
            (11_079, 0.01),
            (26_264, 0.02),
            (41_452, 0.04),
            (57_542, 0.06),
            (72_724, 0.08),
            (371_479, 0.093),
            (445_771, 0.103),
            (742_953, 0.113),
            (1_000_000, 0.123),
            (float("inf"), 0.133),  # 12.3% + 1% Mental Health Services Tax
        ],
        "mfj": [
            (22_158, 0.01),
            (52_528, 0.02),
            (82_904, 0.04),
            (115_084, 0.06),
            (145_448, 0.08),
            (742_958, 0.093),
            (891_542, 0.103),
            (1_485_906, 0.113),
            (2_000_000, 0.123),
            (float("inf"), 0.133),
        ],
        "mfs": [
            (11_079, 0.01),
            (26_264, 0.02),
            (41_452, 0.04),
            (57_542, 0.06),
            (72_724, 0.08),
            (371_479, 0.093),
            (445_771, 0.103),
            (742_953, 0.113),
            (1_000_000, 0.123),
            (float("inf"), 0.133),
        ],
        "hoh": [
            (22_178, 0.01),
            (52_528, 0.02),
            (67_726, 0.04),
            (83_816, 0.06),
            (98_998, 0.08),
            (505_218, 0.093),
            (606_258, 0.103),
            (1_010_418, 0.113),
            (1_000_000, 0.123),
            (float("inf"), 0.133),
        ],
    },
    "NY": {
        "single": [
            (8_500, 0.04),
            (11_700, 0.045),
            (13_900, 0.0525),
            (80_650, 0.0585),
            (215_400, 0.0625),
            (1_077_550, 0.0685),
            (5_000_000, 0.0965),
            (25_000_000, 0.103),
            (float("inf"), 0.109),
        ],
        "mfj": [
            (17_150, 0.04),
            (23_600, 0.045),
            (27_900, 0.0525),
            (161_550, 0.0585),
            (323_200, 0.0625),
            (2_155_350, 0.0685),
            (5_000_000, 0.0965),
            (25_000_000, 0.103),
            (float("inf"), 0.109),
        ],
        "mfs": [
            (8_500, 0.04),
            (11_700, 0.045),
            (13_900, 0.0525),
            (80_650, 0.0585),
            (215_400, 0.0625),
            (1_077_550, 0.0685),
            (5_000_000, 0.0965),
            (25_000_000, 0.103),
            (float("inf"), 0.109),
        ],
        "hoh": [
            (12_800, 0.04),
            (17_650, 0.045),
            (20_900, 0.0525),
            (107_650, 0.0585),
            (269_300, 0.0625),
            (1_616_450, 0.0685),
            (5_000_000, 0.0965),
            (25_000_000, 0.103),
            (float("inf"), 0.109),
        ],
    },
    "NJ": {
        "single": [
            (20_000, 0.014),
            (35_000, 0.0175),
            (40_000, 0.035),
            (75_000, 0.05525),
            (500_000, 0.0637),
            (1_000_000, 0.0897),
            (float("inf"), 0.1075),
        ],
        "mfj": [
            (20_000, 0.014),
            (50_000, 0.0175),
            (70_000, 0.0245),
            (80_000, 0.035),
            (150_000, 0.05525),
            (500_000, 0.0637),
            (1_000_000, 0.0897),
            (float("inf"), 0.1075),
        ],
        "mfs": [
            (20_000, 0.014),
            (35_000, 0.0175),
            (40_000, 0.035),
            (75_000, 0.05525),
            (500_000, 0.0637),
            (1_000_000, 0.0897),
            (float("inf"), 0.1075),
        ],
        "hoh": [
            (20_000, 0.014),
            (50_000, 0.0175),
            (70_000, 0.0245),
            (80_000, 0.035),
            (150_000, 0.05525),
            (500_000, 0.0637),
            (1_000_000, 0.0897),
            (float("inf"), 0.1075),
        ],
    },
    "OR": {
        "single": [
            (4_050, 0.0475),
            (10_200, 0.0675),
            (125_000, 0.0875),
            (float("inf"), 0.099),
        ],
        "mfj": [
            (8_100, 0.0475),
            (20_400, 0.0675),
            (250_000, 0.0875),
            (float("inf"), 0.099),
        ],
        "mfs": [
            (4_050, 0.0475),
            (10_200, 0.0675),
            (125_000, 0.0875),
            (float("inf"), 0.099),
        ],
        "hoh": [
            (8_100, 0.0475),
            (20_400, 0.0675),
            (250_000, 0.0875),
            (float("inf"), 0.099),
        ],
    },
    "MN": {
        "single": [
            (31_690, 0.0535),
            (104_090, 0.068),
            (183_340, 0.0785),
            (float("inf"), 0.0985),
        ],
        "mfj": [
            (46_330, 0.0535),
            (184_040, 0.068),
            (321_450, 0.0785),
            (float("inf"), 0.0985),
        ],
        "mfs": [
            (23_165, 0.0535),
            (92_020, 0.068),
            (160_725, 0.0785),
            (float("inf"), 0.0985),
        ],
        "hoh": [
            (39_010, 0.0535),
            (156_570, 0.068),
            (264_900, 0.0785),
            (float("inf"), 0.0985),
        ],
    },
    "HI": {
        "single": [
            (2_400, 0.014),
            (4_800, 0.032),
            (9_600, 0.055),
            (14_400, 0.064),
            (19_200, 0.068),
            (24_000, 0.072),
            (36_000, 0.076),
            (48_000, 0.079),
            (150_000, 0.0825),
            (175_000, 0.09),
            (200_000, 0.10),
            (float("inf"), 0.11),
        ],
        "mfj": [
            (4_800, 0.014),
            (9_600, 0.032),
            (19_200, 0.055),
            (28_800, 0.064),
            (38_400, 0.068),
            (48_000, 0.072),
            (72_000, 0.076),
            (96_000, 0.079),
            (300_000, 0.0825),
            (350_000, 0.09),
            (400_000, 0.10),
            (float("inf"), 0.11),
        ],
        "mfs": [
            (2_400, 0.014),
            (4_800, 0.032),
            (9_600, 0.055),
            (14_400, 0.064),
            (19_200, 0.068),
            (24_000, 0.072),
            (36_000, 0.076),
            (48_000, 0.079),
            (150_000, 0.0825),
            (175_000, 0.09),
            (200_000, 0.10),
            (float("inf"), 0.11),
        ],
        "hoh": [
            (3_600, 0.014),
            (7_200, 0.032),
            (14_400, 0.055),
            (21_600, 0.064),
            (28_800, 0.068),
            (36_000, 0.072),
            (54_000, 0.076),
            (72_000, 0.079),
            (225_000, 0.0825),
            (262_500, 0.09),
            (300_000, 0.10),
            (float("inf"), 0.11),
        ],
    },
    "DC": {
        "single": [
            (10_000, 0.04),
            (40_000, 0.06),
            (60_000, 0.065),
            (250_000, 0.085),
            (500_000, 0.0925),
            (1_000_000, 0.0975),
            (float("inf"), 0.1075),
        ],
        "mfj": [
            (10_000, 0.04),
            (40_000, 0.06),
            (60_000, 0.065),
            (250_000, 0.085),
            (500_000, 0.0925),
            (1_000_000, 0.0975),
            (float("inf"), 0.1075),
        ],
        "mfs": [
            (10_000, 0.04),
            (40_000, 0.06),
            (60_000, 0.065),
            (250_000, 0.085),
            (500_000, 0.0925),
            (1_000_000, 0.0975),
            (float("inf"), 0.1075),
        ],
        "hoh": [
            (10_000, 0.04),
            (40_000, 0.06),
            (60_000, 0.065),
            (250_000, 0.085),
            (500_000, 0.0925),
            (1_000_000, 0.0975),
            (float("inf"), 0.1075),
        ],
    },
}

# NYC local income tax (2025) — applies on top of NY state tax
NYC_BRACKETS = {
    "single": [
        (12_000, 0.03078),
        (25_000, 0.03762),
        (50_000, 0.03819),
        (float("inf"), 0.03876),
    ],
    "mfj": [
        (21_600, 0.03078),
        (45_000, 0.03762),
        (90_000, 0.03819),
        (float("inf"), 0.03876),
    ],
    "mfs": [
        (12_000, 0.03078),
        (25_000, 0.03762),
        (50_000, 0.03819),
        (float("inf"), 0.03876),
    ],
    "hoh": [
        (14_400, 0.03078),
        (30_000, 0.03762),
        (60_000, 0.03819),
        (float("inf"), 0.03876),
    ],
}

# State standard deductions (2025, where applicable)
STATE_STANDARD_DEDUCTION = {
    "CA": {
        "single": 5_706,
        "mfj": 11_412,
        "mfs": 5_706,
        "hoh": 11_412,
    },
    "NY": {
        "single": 8_000,
        "mfj": 16_050,
        "mfs": 8_000,
        "hoh": 11_200,
    },
    "OR": {
        "single": 2_745,
        "mfj": 5_495,
        "mfs": 2_745,
        "hoh": 4_435,
    },
}

# States that have their own standard deduction
# States not listed here either have no income tax, use federal AGI directly,
# or have their own adjustments (handled case-by-case)
STATES_WITH_STD_DEDUCTION = set(STATE_STANDARD_DEDUCTION.keys())


def _calculate_progressive_tax(taxable_income, brackets):
    """Calculate tax using progressive brackets.

    Args:
        taxable_income: State taxable income.
        brackets: List of (upper_limit, rate) tuples.

    Returns:
        dict with tax, effective rate, and breakdown.
    """
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
                "rate": f"{rate:.2%}",
                "income": round(bracket_income),
                "tax": round(bracket_tax, 2),
            })
        prev_limit = limit

    return {
        "tax": round(tax, 2),
        "effective_rate": round(tax / taxable_income, 4) if taxable_income > 0 else 0,
        "breakdown": breakdown,
    }


def calculate_state_tax(
    state,
    taxable_income,
    status,
    year=2025,
    nyc_resident=False,
):
    """Calculate state income tax.

    Args:
        state: Two-letter state code (e.g., 'CA', 'TX').
        taxable_income: State taxable income (after state deductions).
        status: Filing status ('single', 'mfj', 'mfs', 'hoh').
        year: Tax year.
        nyc_resident: If True and state is NY, add NYC local tax.

    Returns:
        dict with state tax, local tax, total, and details.
    """
    state = state.upper()

    if state in NO_TAX_STATES:
        return {
            "state": state,
            "state_tax": 0,
            "local_tax": 0,
            "total_tax": 0,
            "note": "No state income tax",
        }

    if state in FLAT_RATE:
        rate = FLAT_RATE[state]
        tax = round(taxable_income * rate, 2)
        return {
            "state": state,
            "rate": rate,
            "taxable_income": round(taxable_income),
            "state_tax": tax,
            "local_tax": 0,
            "total_tax": tax,
            "effective_rate": round(tax / taxable_income, 4) if taxable_income > 0 else 0,
        }

    if state in PROGRESSIVE_BRACKETS:
        brackets = PROGRESSIVE_BRACKETS[state]
        status_key = status if status in brackets else "single"
        result = _calculate_progressive_tax(taxable_income, brackets[status_key])

        local_tax = 0
        local_detail = None
        if state == "NY" and nyc_resident:
            nyc_status = status if status in NYC_BRACKETS else "single"
            local_detail = _calculate_progressive_tax(taxable_income, NYC_BRACKETS[nyc_status])
            local_tax = local_detail["tax"]

        total = result["tax"] + local_tax
        output = {
            "state": state,
            "taxable_income": round(taxable_income),
            "state_tax": result["tax"],
            "state_effective_rate": result["effective_rate"],
            "state_breakdown": result["breakdown"],
            "local_tax": local_tax,
            "total_tax": round(total, 2),
            "effective_rate": round(total / taxable_income, 4) if taxable_income > 0 else 0,
        }
        if local_detail:
            output["local_breakdown"] = local_detail["breakdown"]
            output["local_label"] = "NYC"
        return output

    return {
        "state": state,
        "state_tax": 0,
        "local_tax": 0,
        "total_tax": 0,
        "note": f"State '{state}' not in database — add brackets or use flat rate manually",
    }


def get_state_standard_deduction(state, status):
    """Get the state standard deduction if applicable.

    Args:
        state: Two-letter state code.
        status: Filing status.

    Returns:
        Deduction amount, or 0 if state has no standard deduction in our database.
    """
    state = state.upper()
    if state in STATE_STANDARD_DEDUCTION:
        deductions = STATE_STANDARD_DEDUCTION[state]
        return deductions.get(status, deductions.get("single", 0))
    return 0


def get_supported_states():
    """Return all states supported by this calculator."""
    progressive = set(PROGRESSIVE_BRACKETS.keys())
    flat = set(FLAT_RATE.keys())
    no_tax = NO_TAX_STATES
    return sorted(progressive | flat | no_tax)


def main():
    parser = argparse.ArgumentParser(description="Calculate state income tax")
    parser.add_argument(
        "--state", required=True, help="Two-letter state code (e.g., CA, NY, TX)"
    )
    parser.add_argument("--income", type=float, required=True, help="State taxable income")
    parser.add_argument(
        "--status",
        choices=["single", "mfj", "mfs", "hoh"],
        required=True,
        help="Filing status",
    )
    parser.add_argument("--year", type=int, default=2025, help="Tax year")
    parser.add_argument("--nyc", action="store_true", help="NYC resident (adds local tax)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--list-states", action="store_true", help="List all supported states"
    )

    args = parser.parse_args()

    if args.list_states:
        states = get_supported_states()
        print(f"Supported states ({len(states)}): {', '.join(states)}")
        return

    result = calculate_state_tax(
        state=args.state,
        taxable_income=args.income,
        status=args.status,
        year=args.year,
        nyc_resident=args.nyc,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'=' * 60}")
        print(f"  State Tax Calculation — {args.state.upper()} {args.year} ({args.status.upper()})")
        print(f"{'=' * 60}")

        if result.get("note"):
            print(f"\n  {result['note']}")
        else:
            print(f"\n  Taxable Income: ${args.income:,.0f}")

            if result.get("state_breakdown"):
                print(f"\n  State Bracket Breakdown:")
                for b in result["state_breakdown"]:
                    print(f"    {b['rate']:>6s}  {b['range']:<40s}  ${b['tax']:>10,.2f}")

            if result.get("rate"):
                print(f"\n  Flat Rate: {result['rate']:.2%}")

            print(f"\n  State Tax:   ${result['state_tax']:>10,.2f}")

            if result["local_tax"] > 0:
                label = result.get("local_label", "Local")
                print(f"  {label} Tax:     ${result['local_tax']:>10,.2f}")
                if result.get("local_breakdown"):
                    for b in result["local_breakdown"]:
                        print(f"    {b['rate']:>6s}  {b['range']:<40s}  ${b['tax']:>10,.2f}")

            print(f"\n  {'TOTAL STATE TAX':>40s}  ${result['total_tax']:>10,.2f}")
            print(f"  {'Effective Rate':>40s}  {result.get('effective_rate', 0):.2%}")

        print()


if __name__ == "__main__":
    main()
