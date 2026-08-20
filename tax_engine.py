"""Transparent 2025 U.S. tax-estimation helpers used by the Streamlit UI."""

from __future__ import annotations


TAX_YEAR = 2025
CHILD_TAX_CREDIT = 2_200
SOCIAL_SECURITY_WAGE_BASE = 176_100
RETIREMENT_LIMIT = 23_500
HSA_LIMITS = {"Self-only HDHP": 4_300, "Family HDHP": 8_550}

BRACKETS = {
    "Single": [(11925, .10), (48475, .12), (103350, .22), (197300, .24), (250525, .32), (626350, .35), (float("inf"), .37)],
    "Married filing jointly": [(23850, .10), (96950, .12), (206700, .22), (394600, .24), (501050, .32), (751600, .35), (float("inf"), .37)],
    "Head of household": [(17000, .10), (64850, .12), (103350, .22), (197300, .24), (250500, .32), (626350, .35), (float("inf"), .37)],
    "Married filing separately": [(11925, .10), (48475, .12), (103350, .22), (197300, .24), (250525, .32), (375800, .35), (float("inf"), .37)],
}

STANDARD_DEDUCTION = {
    "Single": 15_000,
    "Married filing jointly": 30_000,
    "Head of household": 22_500,
    "Married filing separately": 15_000,
}

# This is a coarse educational profile, not a state tax engine. Rates approximate
# a typical effective burden on taxable wages; the UI shows that caveat.
NO_WAGE_TAX = {"Alaska", "Florida", "Nevada", "New Hampshire", "South Dakota", "Tennessee", "Texas", "Washington", "Wyoming"}
LOW = {"Arizona", "Colorado", "Indiana", "Kentucky", "Louisiana", "Michigan", "Mississippi", "North Carolina", "North Dakota", "Ohio", "Pennsylvania", "Utah"}
HIGH = {"California", "Connecticut", "District of Columbia", "Hawaii", "Maine", "Minnesota", "New Jersey", "New York", "Oregon", "Vermont"}
STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
STATE_PROFILES = {s: (0 if s in NO_WAGE_TAX else .035 if s in LOW else .06 if s in HIGH else .045) for s in STATES}

# Approximate FY2024 shares of $6.75T total outlays, assembled from CBO's FY2024
# summary. Categories are intentionally broad and sum to 100%.
SPENDING_SHARES = {
    "Social Security": .2145,
    "Medicare": .1289,
    "Medicaid & health programs": .1190,
    "Defense": .1290,
    "Income security": .0860,
    "Net interest": .1300,
    "Veterans": .0480,
    "Transportation & infrastructure": .0300,
    "Education & training": .0250,
    "Other federal programs": .0896,
}

# FY2024 agency-level proxy shares. Benefit payments and interest are grouped
# under their administering entity, then normalized to 100%.
AGENCY_SHARES = {
    "Health & Human Services": .250,
    "Social Security Administration": .215,
    "Treasury (including net interest)": .140,
    "Department of Defense": .130,
    "Veterans Affairs": .050,
    "Agriculture": .040,
    "Education": .039,
    "Transportation": .025,
    "Homeland Security": .017,
    "Justice": .007,
    "NASA": .004,
    "Environmental Protection Agency": .002,
    "All other agencies": .081,
}


def progressive_tax(taxable: float, brackets: list[tuple[float, float]]) -> tuple[float, float]:
    tax = 0.0
    lower = 0.0
    marginal = 0.0
    for upper, rate in brackets:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
            marginal = rate
        if taxable <= upper:
            break
        lower = upper
    return tax, marginal


def calculate_estimate(
    filing_status: str,
    wages: float,
    other_income: float,
    pretax_contributions: float,
    itemized_deductions: float,
    qualifying_children: int,
    state: str,
    federal_withholding: float = 0,
) -> dict[str, float | str]:
    """Return a simplified federal, employee-payroll, and state estimate."""
    gross = max(0, wages + other_income)
    pretax = min(max(0, pretax_contributions), gross)
    deduction = max(STANDARD_DEDUCTION[filing_status], max(0, itemized_deductions))
    taxable = max(0, gross - pretax - deduction)
    federal_precredit, marginal = progressive_tax(taxable, BRACKETS[filing_status])

    phaseout_start = 400_000 if filing_status == "Married filing jointly" else 200_000
    phaseout = max(0, ((max(0, gross - phaseout_start) + 999) // 1_000) * 50)
    eligible_credit = max(0, qualifying_children * CHILD_TAX_CREDIT - phaseout)
    child_credit = min(federal_precredit, eligible_credit)  # nonrefundable portion only
    federal = max(0, federal_precredit - child_credit)

    ss = min(max(0, wages), SOCIAL_SECURITY_WAGE_BASE) * .062
    medicare = max(0, wages) * .0145
    addl_threshold = 250_000 if filing_status == "Married filing jointly" else 125_000 if filing_status == "Married filing separately" else 200_000
    medicare += max(0, wages - addl_threshold) * .009

    state_base = max(0, gross - pretax - STANDARD_DEDUCTION[filing_status] * .55)
    state_tax = state_base * STATE_PROFILES[state]
    total = federal + ss + medicare + state_tax
    withholding = max(0, federal_withholding)
    return {
        "gross_income": gross,
        "pretax_contributions": pretax,
        "standard_deduction": STANDARD_DEDUCTION[filing_status],
        "deduction_used": deduction,
        "taxable_income": taxable,
        "federal_before_credits": federal_precredit,
        "child_credit_used": child_credit,
        "federal_income_tax": federal,
        "social_security": ss,
        "medicare": medicare,
        "state_income_tax": state_tax,
        "total_tax": total,
        "take_home": max(0, gross - pretax - total),
        "effective_rate": total / gross if gross else 0,
        "federal_effective_rate": federal / gross if gross else 0,
        "marginal_rate": marginal,
        "federal_withholding": withholding,
        "refund_or_due": withholding - federal,
        "state_note": "no broad wage tax" if state in NO_WAGE_TAX else "rough effective-rate proxy",
    }


def project_withholding(
    federal_tax: float,
    withheld_year_to_date: float,
    paychecks_remaining: int,
    withholding_per_future_paycheck: float,
) -> dict[str, float | str]:
    """Project year-end federal withholding and a per-paycheck course correction."""
    ytd = max(0, withheld_year_to_date)
    remaining = max(0, int(paychecks_remaining))
    current_per_check = max(0, withholding_per_future_paycheck)
    projected_future = remaining * current_per_check
    projected_total = ytd + projected_future
    balance = projected_total - max(0, federal_tax)
    target_per_check = max(0, (max(0, federal_tax) - ytd) / remaining) if remaining else 0
    adjustment = target_per_check - current_per_check if remaining else 0
    status = "refund" if balance > 1 else "amount due" if balance < -1 else "near zero"
    return {
        "withheld_year_to_date": ytd,
        "projected_future_withholding": projected_future,
        "projected_total_withholding": projected_total,
        "projected_balance": balance,
        "target_per_paycheck": target_per_check,
        "per_paycheck_adjustment": adjustment,
        "status": status,
    }


def incremental_tax_breakdown(base_inputs: dict, extra_wages: float) -> dict[str, float]:
    """Show what happens to an additional amount of wage income."""
    base = calculate_estimate(**base_inputs)
    changed_inputs = dict(base_inputs)
    changed_inputs["wages"] = max(0, changed_inputs["wages"] + max(0, extra_wages))
    changed = calculate_estimate(**changed_inputs)
    federal = changed["federal_income_tax"] - base["federal_income_tax"]
    social_security = changed["social_security"] - base["social_security"]
    medicare = changed["medicare"] - base["medicare"]
    state = changed["state_income_tax"] - base["state_income_tax"]
    kept = changed["take_home"] - base["take_home"]
    return {
        "extra_wages": max(0, extra_wages),
        "federal_income_tax": federal,
        "social_security": social_security,
        "medicare": medicare,
        "state_income_tax": state,
        "kept": kept,
        "combined_incremental_rate": 1 - kept / extra_wages if extra_wages else 0,
    }


def student_loan_interest_deduction(filing_status: str, gross_income: float, interest_paid: float) -> float:
    """Simplified 2025 student-loan-interest deduction and income phaseout."""
    if filing_status == "Married filing separately":
        return 0
    amount = min(2_500, max(0, interest_paid))
    lower, upper = ((170_000, 200_000) if filing_status == "Married filing jointly" else (85_000, 100_000))
    if gross_income <= lower:
        return amount
    if gross_income >= upper:
        return 0
    return amount * (upper - gross_income) / (upper - lower)


def _education_credit(filing_status: str, gross_income: float, education_expenses: float) -> float:
    if filing_status == "Married filing separately" or education_expenses <= 0:
        return 0
    tentative = min(2_000, education_expenses) + min(2_000, max(0, education_expenses - 2_000)) * .25
    lower, upper = ((160_000, 180_000) if filing_status == "Married filing jointly" else (80_000, 90_000))
    if gross_income <= lower:
        return tentative
    if gross_income >= upper:
        return 0
    return tentative * (upper - gross_income) / (upper - lower)


def _dependent_care_credit(gross_income: float, qualifying_people: int, expenses: float) -> float:
    if qualifying_people <= 0 or expenses <= 0:
        return 0
    eligible_expenses = min(expenses, 3_000 if qualifying_people == 1 else 6_000)
    # The statutory rate slides from 35% to a 20% floor as AGI rises.
    reductions = max(0, int((gross_income - 15_000 + 1_999) // 2_000))
    rate = max(.20, .35 - reductions * .01)
    return eligible_expenses * rate


def opportunity_screen(
    *,
    filing_status: str,
    gross_income: float,
    earned_income: float,
    marginal_rate: float,
    qualifying_children: int,
    age: int,
    retirement_contributions: float,
    hsa_coverage: str,
    hsa_contributions: float,
    dependent_care_expenses: float,
    education_expenses: float,
    student_loan_interest: float,
) -> list[dict[str, float | str]]:
    """Return personalized leads, not determinations of eligibility."""
    items: list[dict[str, float | str]] = []

    catch_up = 11_250 if 60 <= age <= 63 else 7_500 if age >= 50 else 0
    retirement_room = max(0, RETIREMENT_LIMIT + catch_up - max(0, retirement_contributions))
    if earned_income > 0 and retirement_room > 0:
        example_contribution = min(retirement_room, 5_000, max(0, earned_income - retirement_contributions))
        items.append({
            "title": "Workplace retirement contribution",
            "estimate": example_contribution * marginal_rate,
            "detail": f"You appear to have about ${retirement_room:,.0f} of room under the simplified 2025 employee limit. A ${example_contribution:,.0f} additional pre-tax contribution could reduce federal income tax by roughly ${example_contribution * marginal_rate:,.0f} at your current marginal rate.",
            "next_step": "Check plan eligibility, employer matching, and payroll deadlines.",
        })

    if hsa_coverage in HSA_LIMITS:
        hsa_limit = HSA_LIMITS[hsa_coverage] + (1_000 if age >= 55 else 0)
        hsa_room = max(0, hsa_limit - max(0, hsa_contributions))
        if hsa_room > 0:
            items.append({
                "title": "Health Savings Account",
                "estimate": hsa_room * marginal_rate,
                "detail": f"Your selected coverage suggests up to ${hsa_room:,.0f} of remaining 2025 HSA room. If fully deductible, that amount could reduce federal income tax by roughly ${hsa_room * marginal_rate:,.0f}.",
                "next_step": "Confirm HDHP eligibility, coverage dates, employer deposits, and Medicare status.",
            })

    care_credit = _dependent_care_credit(gross_income, qualifying_children, dependent_care_expenses)
    if care_credit > 0:
        items.append({
            "title": "Child and dependent care credit",
            "estimate": care_credit,
            "detail": f"The expenses entered produce a rough nonrefundable credit screen of ${care_credit:,.0f}. Work-related care, provider, earned-income, and qualifying-person tests apply.",
            "next_step": "Review Form 2441 requirements and any dependent-care FSA benefits.",
        })

    education_credit = _education_credit(filing_status, gross_income, education_expenses)
    if education_expenses > 0:
        items.append({
            "title": "Education credit",
            "estimate": education_credit,
            "detail": f"The expenses entered produce an American Opportunity Credit screen of about ${education_credit:,.0f}; the Lifetime Learning Credit may be a better fit in some cases. The same expenses cannot support multiple benefits.",
            "next_step": "Confirm student eligibility, Form 1098-T amounts, scholarships, and income limits.",
        })

    loan_deduction = student_loan_interest_deduction(filing_status, gross_income, student_loan_interest)
    if student_loan_interest > 0:
        items.append({
            "title": "Student-loan interest deduction",
            "estimate": loan_deduction * marginal_rate,
            "detail": f"About ${loan_deduction:,.0f} of the interest entered may survive the simplified income phaseout, with an illustrative federal tax effect of ${loan_deduction * marginal_rate:,.0f}.",
            "next_step": "Check Form 1098-E, legal obligation, dependency status, and loan eligibility.",
        })

    savers_limit = 79_000 if filing_status == "Married filing jointly" else 59_250 if filing_status == "Head of household" else 39_500
    if 0 < retirement_contributions and gross_income <= savers_limit and age >= 18:
        max_credit = 2_000 if filing_status == "Married filing jointly" else 1_000
        items.append({
            "title": "Saver's Credit screening flag",
            "estimate": max_credit,
            "detail": f"Your income is below the broad 2025 ${savers_limit:,.0f} screen. The actual credit is 10%, 20%, or 50% of eligible contributions and may be lower than the maximum shown.",
            "next_step": "Confirm that you are not a dependent or full-time student and review Form 8880.",
        })

    eitc_max = {0: 649, 1: 4_328, 2: 7_152}.get(min(qualifying_children, 3), 8_046)
    broad_eitc_limit = 68_675 if filing_status == "Married filing jointly" else 61_555
    if 0 < earned_income <= broad_eitc_limit:
        items.append({
            "title": "Earned Income Tax Credit eligibility check",
            "estimate": eitc_max,
            "detail": f"Your earned income is within a broad screening range. The amount shown is the 2025 maximum for the child count entered, not an estimate of your credit.",
            "next_step": "Use the IRS EITC Assistant; age, residency, investment-income, SSN, and qualifying-child rules matter.",
        })

    return items


def allocate_federal_income_tax(amount: float) -> list[tuple[str, float]]:
    return [(category, amount * share) for category, share in SPENDING_SHARES.items()]


def allocate_by_agency(amount: float) -> list[tuple[str, float]]:
    return [(agency, amount * share) for agency, share in AGENCY_SHARES.items()]


def ukraine_scale_estimate(federal_income_tax: float) -> float:
    # $174.2B appropriated, compared with roughly $19.15T FY22-FY24 outlays.
    return federal_income_tax * 174.2 / 19_150
