"""
Deduction calculations — SALT cap, mortgage interest, itemized vs standard.

Usage:
    python3 deductions.py --state-tax 24585 --property-tax 8031 --mortgage-interest 37128 \
        --status mfj --agi 411205 --filing-type ra --year 2025
"""

import argparse
import json

# 2025 SALT Cap (OBBB, signed July 4, 2025 — retroactive to 2025)
# Source: https://dhjj.com/salt-deduction-2025-phaseouts/
# Cap phases down by 30 cents per dollar of MAGI over threshold.
# MFS floor is $5,000 (not $10,000). Thresholds increase 1%/year through 2029.
SALT_CAP = {
    2025: {
        "base": {
            "single": 40_000,
            "mfj": 40_000,
            "mfs": 20_000,
            "hoh": 40_000,
        },
        "phase_down": {
            "threshold": {
                "single": 500_000,
                "mfj": 500_000,
                "mfs": 250_000,
                "hoh": 500_000,
            },
            "rate": 0.30,
        },
        "floor": {
            "single": 10_000,
            "mfj": 10_000,
            "mfs": 5_000,
            "hoh": 10_000,
        },
    },
}

# Mortgage Interest Limits
MORTGAGE_LIMITS = {
    # Loans originated after Dec 15, 2017
    "post_tcja": {
        "mfj": 750_000,
        "mfs": 375_000,
        "single": 750_000,
        "hoh": 750_000,
    },
    # Loans originated on or before Dec 15, 2017
    "pre_tcja": {
        "mfj": 1_000_000,
        "mfs": 500_000,
        "single": 1_000_000,
        "hoh": 1_000_000,
    },
}

# Standard Deductions (post-OBBB)
# Source: https://www.nerdwallet.com/taxes/learn/standard-deduction
STANDARD_DEDUCTION = {
    2025: {
        "single": 15_750,
        "mfj": 31_500,
        "mfs": 15_750,
        "hoh": 23_625,
    },
}


def calculate_salt_cap(total_salt, agi, status, year=2025):
    """Calculate the SALT deduction after applying the cap and phase-down.

    2025 rules (OBBB): $40,000 base ($20,000 MFS), reduced by 30% of MAGI over
    threshold, floor of $10,000 ($5,000 MFS).

    Args:
        total_salt: Total state/local taxes (income tax + property tax + car VLF + SDI).
        agi: Adjusted gross income.
        status: Filing status.
        year: Tax year.

    Returns:
        dict with allowed SALT deduction and calculation details.
    """
    config = SALT_CAP[year]
    base_cap = config["base"][status]
    threshold = config["phase_down"]["threshold"][status]
    phase_rate = config["phase_down"]["rate"]
    floor = config["floor"][status]

    if agi <= threshold:
        effective_cap = base_cap
        phase_down_amount = 0
    else:
        excess = agi - threshold
        phase_down_amount = round(excess * phase_rate)
        effective_cap = max(base_cap - phase_down_amount, floor)

    allowed = min(total_salt, effective_cap)

    return {
        "total_salt_before_cap": round(total_salt),
        "base_cap": base_cap,
        "agi": round(agi),
        "threshold": threshold,
        "phase_down_amount": phase_down_amount,
        "effective_cap": effective_cap,
        "allowed_deduction": round(allowed),
        "disallowed": round(total_salt - allowed),
    }


def calculate_mortgage_interest_deduction(
    interest_paid, loan_balance, loan_origination_date, status, is_nra=False
):
    """Calculate deductible mortgage interest.

    NRAs CANNOT deduct personal mortgage interest on 1040-NR.

    Args:
        interest_paid: Total mortgage interest from 1098(s).
        loan_balance: Outstanding mortgage principal.
        loan_origination_date: Date string (YYYY-MM-DD) for TCJA threshold.
        status: Filing status.
        is_nra: If True, returns 0 (NRAs can't deduct mortgage interest).

    Returns:
        dict with deductible amount and limit details.
    """
    if is_nra:
        return {
            "interest_paid": round(interest_paid),
            "deductible": 0,
            "reason": "NRAs cannot deduct personal mortgage interest on 1040-NR",
        }

    if loan_origination_date >= "2017-12-16":
        limit = MORTGAGE_LIMITS["post_tcja"][status]
    else:
        limit = MORTGAGE_LIMITS["pre_tcja"][status]

    if loan_balance <= limit:
        deductible = interest_paid
        ratio = 1.0
    else:
        ratio = limit / loan_balance
        deductible = interest_paid * ratio

    return {
        "interest_paid": round(interest_paid),
        "loan_balance": round(loan_balance),
        "limit": limit,
        "deduction_ratio": round(ratio, 4),
        "deductible": round(deductible),
    }


def calculate_itemized_deductions(
    state_income_tax=0,
    property_tax=0,
    car_vlf=0,
    sdi=0,
    mortgage_interest=0,
    loan_balance=0,
    loan_origination_date="2024-01-01",
    charitable=0,
    other=0,
    agi=0,
    status="single",
    is_nra=False,
    year=2025,
):
    """Calculate total itemized deductions.

    Args:
        state_income_tax: State income tax withheld.
        property_tax: Real estate tax paid.
        car_vlf: Vehicle license fee (deductible portion of car registration).
        sdi: State disability insurance.
        mortgage_interest: From 1098.
        loan_balance: Outstanding principal for mortgage limit.
        loan_origination_date: For TCJA threshold.
        charitable: Charitable contributions.
        other: Other deductible amounts.
        agi: Adjusted gross income.
        status: Filing status.
        is_nra: Nonresident alien flag.
        year: Tax year.

    Returns:
        dict with all deduction components and total.
    """
    total_salt = state_income_tax + property_tax + car_vlf + sdi
    salt = calculate_salt_cap(total_salt, agi, status, year)

    mortgage = calculate_mortgage_interest_deduction(
        mortgage_interest, loan_balance, loan_origination_date, status, is_nra
    )

    total = salt["allowed_deduction"] + mortgage["deductible"] + charitable + other

    return {
        "salt": salt,
        "mortgage": mortgage,
        "charitable": round(charitable),
        "other": round(other),
        "total_itemized": round(total),
    }


def compare_standard_vs_itemized(itemized_total, status, year=2025, is_nra=False):
    """Compare itemized deductions against the standard deduction.

    NRAs cannot take the standard deduction (except India treaty).

    Args:
        itemized_total: Total itemized deductions.
        status: Filing status.
        year: Tax year.
        is_nra: If True, must itemize (no standard deduction).

    Returns:
        dict with recommendation.
    """
    if is_nra:
        return {
            "standard": 0,
            "itemized": round(itemized_total),
            "recommended": "itemized",
            "deduction": round(itemized_total),
            "note": "NRAs cannot take the standard deduction",
        }

    standard = STANDARD_DEDUCTION[year][status]
    if itemized_total > standard:
        return {
            "standard": standard,
            "itemized": round(itemized_total),
            "recommended": "itemized",
            "deduction": round(itemized_total),
            "savings_vs_standard": round(itemized_total - standard),
        }
    else:
        return {
            "standard": standard,
            "itemized": round(itemized_total),
            "recommended": "standard",
            "deduction": standard,
            "savings_vs_itemized": standard - round(itemized_total),
        }


def main():
    parser = argparse.ArgumentParser(description="Calculate deductions")
    parser.add_argument("--state-tax", type=float, default=0)
    parser.add_argument("--property-tax", type=float, default=0)
    parser.add_argument("--car-vlf", type=float, default=0)
    parser.add_argument("--sdi", type=float, default=0)
    parser.add_argument("--mortgage-interest", type=float, default=0)
    parser.add_argument("--loan-balance", type=float, default=0)
    parser.add_argument("--loan-date", default="2024-01-01")
    parser.add_argument("--charitable", type=float, default=0)
    parser.add_argument("--agi", type=float, required=True)
    parser.add_argument(
        "--status", choices=["single", "mfj", "mfs", "hoh"], required=True
    )
    parser.add_argument(
        "--filing-type", choices=["ra", "nra"], required=True
    )
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    is_nra = args.filing_type == "nra"

    itemized = calculate_itemized_deductions(
        state_income_tax=args.state_tax,
        property_tax=args.property_tax,
        car_vlf=args.car_vlf,
        sdi=args.sdi,
        mortgage_interest=args.mortgage_interest,
        loan_balance=args.loan_balance,
        loan_origination_date=args.loan_date,
        charitable=args.charitable,
        agi=args.agi,
        status=args.status,
        is_nra=is_nra,
        year=args.year,
    )

    comparison = compare_standard_vs_itemized(
        itemized["total_itemized"], args.status, args.year, is_nra
    )

    result = {"itemized": itemized, "comparison": comparison}

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(
            f"  Deduction Analysis — {args.year} "
            f"({args.status.upper()}, {'NRA' if is_nra else 'RA'})"
        )
        print(f"{'=' * 60}")
        print(f"\n  SALT:")
        print(f"    State income tax:    ${args.state_tax:>10,.0f}")
        print(f"    Property tax:        ${args.property_tax:>10,.0f}")
        if args.car_vlf:
            print(f"    Vehicle license fee: ${args.car_vlf:>10,.0f}")
        if args.sdi:
            print(f"    State disability:    ${args.sdi:>10,.0f}")
        s = itemized["salt"]
        print(f"    Total before cap:    ${s['total_salt_before_cap']:>10,}")
        print(f"    Cap ({args.status.upper()}):          ${s['effective_cap']:>10,}")
        if s["phase_down_amount"] > 0:
            print(f"    Phase-down:          ${s['phase_down_amount']:>10,}")
        print(f"    Allowed:             ${s['allowed_deduction']:>10,}")
        if s["disallowed"] > 0:
            print(f"    Disallowed:          ${s['disallowed']:>10,}")

        m = itemized["mortgage"]
        print(f"\n  Mortgage Interest:")
        print(f"    Interest paid:       ${m['interest_paid']:>10,}")
        print(f"    Deductible:          ${m['deductible']:>10,}")
        if m.get("reason"):
            print(f"    Note: {m['reason']}")

        c = comparison
        print(f"\n  {'─' * 40}")
        print(f"  Total itemized:        ${c['itemized']:>10,}")
        if not is_nra:
            print(f"  Standard deduction:    ${c['standard']:>10,}")
        print(f"  Recommended:           {c['recommended'].upper()}")
        print(f"  Deduction used:        ${c['deduction']:>10,}")
        print()


if __name__ == "__main__":
    main()
