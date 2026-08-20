"""Core calculations for the Tax Lens educational estimator.

The functions in this module deliberately favor clear, inspectable estimates over
filing-grade completeness.  They model 2025 federal income tax, employee payroll
tax, and a clearly labeled state-income-tax proxy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Dict, Iterable, List, Tuple


TAX_YEAR = 2025


FILING_LABELS: Dict[str, str] = {
    "single": "Single",
    "married_joint": "Married filing jointly",
    "married_separate": "Married filing separately",
    "head_household": "Head of household",
}


# 2025 ordinary-income brackets. Source: IRS Rev. Proc. 2024-40.
FEDERAL_BRACKETS: Dict[str, List[Tuple[float, float]]] = {
    "single": [
        (11_925, 0.10),
        (48_475, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_525, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
    "married_joint": [
        (23_850, 0.10),
        (96_950, 0.12),
        (206_700, 0.22),
        (394_600, 0.24),
        (501_050, 0.32),
        (751_600, 0.35),
        (float("inf"), 0.37),
    ],
    "married_separate": [
        (11_925, 0.10),
        (48_475, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_525, 0.32),
        (375_800, 0.35),
        (float("inf"), 0.37),
    ],
    "head_household": [
        (17_000, 0.10),
        (64_850, 0.12),
        (103_350, 0.22),
        (197_300, 0.24),
        (250_500, 0.32),
        (626_350, 0.35),
        (float("inf"), 0.37),
    ],
}

STANDARD_DEDUCTION = {
    "single": 15_000.0,
    "married_joint": 30_000.0,
    "married_separate": 15_000.0,
    "head_household": 22_500.0,
}

ADDITIONAL_MEDICARE_THRESHOLD = {
    "single": 200_000.0,
    "married_joint": 250_000.0,
    "married_separate": 125_000.0,
    "head_household": 200_000.0,
}

# These are deliberately rough effective-rate proxies for wage income. They are
# not filing calculations, do not include local taxes, and should not be used to
# prepare a return.
STATE_PROXY_RATES: Dict[str, float] = {
    "Alabama": 0.038,
    "Alaska": 0.0,
    "Arizona": 0.035,
    "Arkansas": 0.040,
    "California": 0.065,
    "Colorado": 0.044,
    "Connecticut": 0.050,
    "Delaware": 0.050,
    "District of Columbia": 0.060,
    "Florida": 0.0,
    "Georgia": 0.046,
    "Hawaii": 0.060,
    "Idaho": 0.050,
    "Illinois": 0.045,
    "Indiana": 0.030,
    "Iowa": 0.040,
    "Kansas": 0.045,
    "Kentucky": 0.040,
    "Louisiana": 0.035,
    "Maine": 0.055,
    "Maryland": 0.055,
    "Massachusetts": 0.050,
    "Michigan": 0.040,
    "Minnesota": 0.060,
    "Mississippi": 0.040,
    "Missouri": 0.040,
    "Montana": 0.050,
    "Nebraska": 0.045,
    "Nevada": 0.0,
    "New Hampshire": 0.0,
    "New Jersey": 0.055,
    "New Mexico": 0.040,
    "New York": 0.060,
    "North Carolina": 0.042,
    "North Dakota": 0.020,
    "Ohio": 0.030,
    "Oklahoma": 0.040,
    "Oregon": 0.070,
    "Pennsylvania": 0.031,
    "Rhode Island": 0.045,
    "South Carolina": 0.050,
    "South Dakota": 0.0,
    "Tennessee": 0.0,
    "Texas": 0.0,
    "Utah": 0.045,
    "Vermont": 0.060,
    "Virginia": 0.047,
    "Washington": 0.0,
    "West Virginia": 0.045,
    "Wisconsin": 0.050,
    "Wyoming": 0.0,
}


@dataclass(frozen=True)
class TaxProfile:
    """Inputs used by the estimator.

    Salary is assumed to be W-2 wages. Other income is included for income-tax
    purposes but not payroll-tax purposes.
    """

    salary: float = 75_000.0
    other_income: float = 0.0
    filing_status: str = "single"
    dependents: int = 0
    state: str = "California"
    retirement_contributions: float = 0.0
    hsa_contributions: float = 0.0
    other_pretax: float = 0.0
    itemized_deductions: float = 0.0
    withholding_ytd: float = 0.0
    pay_periods_completed: int = 0
    pay_periods_per_year: int = 26

    def cleaned(self) -> "TaxProfile":
        """Return non-negative and internally safe inputs."""

        return replace(
            self,
            salary=max(0.0, float(self.salary)),
            other_income=max(0.0, float(self.other_income)),
            dependents=max(0, int(self.dependents)),
            retirement_contributions=max(0.0, float(self.retirement_contributions)),
            hsa_contributions=max(0.0, float(self.hsa_contributions)),
            other_pretax=max(0.0, float(self.other_pretax)),
            itemized_deductions=max(0.0, float(self.itemized_deductions)),
            withholding_ytd=max(0.0, float(self.withholding_ytd)),
            pay_periods_completed=max(0, int(self.pay_periods_completed)),
            pay_periods_per_year=max(1, int(self.pay_periods_per_year)),
        )


@dataclass(frozen=True)
class TaxResult:
    gross_income: float
    pretax_contributions: float
    adjusted_income: float
    deduction: float
    deduction_type: str
    taxable_income: float
    federal_before_credits: float
    child_tax_credit: float
    federal_income_tax: float
    social_security_tax: float
    medicare_tax: float
    additional_medicare_tax: float
    payroll_tax: float
    state_income_tax_proxy: float
    total_estimated_tax: float
    take_home_after_estimated_tax: float
    effective_federal_rate: float
    effective_total_rate: float
    marginal_federal_rate: float
    bracket_rows: Tuple[Dict[str, float], ...]
    projected_withholding: float | None
    projected_refund_or_amount_due: float | None

    def as_dict(self) -> Dict[str, float | str | None]:
        return asdict(self)


def progressive_tax(income: float, brackets: Iterable[Tuple[float, float]]) -> Tuple[float, Tuple[Dict[str, float], ...]]:
    """Compute progressive tax and a transparent bracket-by-bracket audit trail."""

    remaining = max(0.0, income)
    lower = 0.0
    total = 0.0
    rows: List[Dict[str, float]] = []
    for upper, rate in brackets:
        width = max(0.0, upper - lower)
        amount = min(remaining, width)
        tax = amount * rate
        if amount > 0 or upper == float("inf"):
            rows.append(
                {
                    "lower": lower,
                    "upper": upper,
                    "rate": rate,
                    "income_in_bracket": amount,
                    "tax": tax,
                }
            )
        total += tax
        remaining -= amount
        if remaining <= 0:
            break
        lower = upper
    return total, tuple(rows)


def marginal_rate(taxable_income: float, filing_status: str) -> float:
    for upper, rate in FEDERAL_BRACKETS[filing_status]:
        if taxable_income <= upper:
            return rate
    return FEDERAL_BRACKETS[filing_status][-1][1]


def child_tax_credit(profile: TaxProfile, adjusted_income: float, federal_before_credits: float) -> float:
    """A limited, non-refundable educational approximation of the 2025 CTC."""

    if profile.dependents <= 0:
        return 0.0
    phaseout_start = 400_000.0 if profile.filing_status == "married_joint" else 200_000.0
    potential_credit = 2_000.0 * profile.dependents
    phaseout_steps = max(0, int((adjusted_income - phaseout_start + 999) // 1_000))
    phaseout = 50.0 * phaseout_steps
    return max(0.0, min(federal_before_credits, potential_credit - phaseout))


def estimate_tax(profile: TaxProfile) -> TaxResult:
    """Estimate tax components for a profile using the documented simplified rules."""

    profile = profile.cleaned()
    if profile.filing_status not in FILING_LABELS:
        raise ValueError(f"Unsupported filing status: {profile.filing_status}")

    gross_income = profile.salary + profile.other_income
    pretax = min(
        gross_income,
        profile.retirement_contributions + profile.hsa_contributions + profile.other_pretax,
    )
    adjusted_income = max(0.0, gross_income - pretax)
    standard = STANDARD_DEDUCTION[profile.filing_status]
    deduction = max(standard, profile.itemized_deductions)
    deduction_type = "Itemized" if profile.itemized_deductions > standard else "Standard"
    taxable_income = max(0.0, adjusted_income - deduction)
    federal_before_credits, bracket_rows = progressive_tax(
        taxable_income, FEDERAL_BRACKETS[profile.filing_status]
    )
    ctc = child_tax_credit(profile, adjusted_income, federal_before_credits)
    federal_income_tax = max(0.0, federal_before_credits - ctc)

    # Traditional 401(k) deferrals generally do not reduce Social Security and
    # Medicare wages, so this simplified estimator starts payroll tax from wages.
    social_security_tax = min(profile.salary, 176_100.0) * 0.062
    medicare_tax = profile.salary * 0.0145
    additional_medicare_tax = max(
        0.0, profile.salary - ADDITIONAL_MEDICARE_THRESHOLD[profile.filing_status],
    ) * 0.009
    payroll_tax = social_security_tax + medicare_tax + additional_medicare_tax

    state_rate = STATE_PROXY_RATES.get(profile.state, 0.04)
    # A transparent wage-income proxy: state taxable base is not an attempt to
    # recreate each state's deductions, credits, or local tax rules.
    state_taxable_proxy = max(0.0, adjusted_income - 12_000.0)
    state_income_tax_proxy = state_taxable_proxy * state_rate

    total = federal_income_tax + payroll_tax + state_income_tax_proxy
    projected_withholding = None
    refund_or_due = None
    if profile.withholding_ytd > 0 and profile.pay_periods_completed > 0:
        projected_withholding = (
            profile.withholding_ytd
            / profile.pay_periods_completed
            * profile.pay_periods_per_year
        )
        refund_or_due = projected_withholding - total

    return TaxResult(
        gross_income=gross_income,
        pretax_contributions=pretax,
        adjusted_income=adjusted_income,
        deduction=deduction,
        deduction_type=deduction_type,
        taxable_income=taxable_income,
        federal_before_credits=federal_before_credits,
        child_tax_credit=ctc,
        federal_income_tax=federal_income_tax,
        social_security_tax=social_security_tax,
        medicare_tax=medicare_tax,
        additional_medicare_tax=additional_medicare_tax,
        payroll_tax=payroll_tax,
        state_income_tax_proxy=state_income_tax_proxy,
        total_estimated_tax=total,
        take_home_after_estimated_tax=max(0.0, gross_income - pretax - total),
        effective_federal_rate=(federal_income_tax / gross_income if gross_income else 0.0),
        effective_total_rate=(total / gross_income if gross_income else 0.0),
        marginal_federal_rate=marginal_rate(taxable_income, profile.filing_status),
        bracket_rows=bracket_rows,
        projected_withholding=projected_withholding,
        projected_refund_or_amount_due=refund_or_due,
    )


def estimate_marginal_dollar(profile: TaxProfile, additional_income: float = 1_000.0) -> Dict[str, float]:
    """Show the estimated tax impact of additional W-2 wages."""

    additional_income = max(0.0, additional_income)
    baseline = estimate_tax(profile)
    comparison = estimate_tax(replace(profile, salary=profile.salary + additional_income))
    total_change = comparison.total_estimated_tax - baseline.total_estimated_tax
    return {
        "additional_income": additional_income,
        "federal_income_tax": comparison.federal_income_tax - baseline.federal_income_tax,
        "payroll_tax": comparison.payroll_tax - baseline.payroll_tax,
        "state_income_tax_proxy": comparison.state_income_tax_proxy - baseline.state_income_tax_proxy,
        "total_tax": total_change,
        "take_home": additional_income - total_change,
    }


def scenario_profile(profile: TaxProfile, scenario: str, comparison_state: str | None = None) -> TaxProfile:
    """Return a transparent preset scenario for side-by-side comparison."""

    if scenario == "Earn $10,000 more":
        return replace(profile, salary=profile.salary + 10_000.0)
    if scenario == "Contribute $5,000 more to retirement":
        return replace(profile, retirement_contributions=profile.retirement_contributions + 5_000.0)
    if scenario == "Add one dependent":
        return replace(profile, dependents=profile.dependents + 1)
    if scenario == "Move to comparison state":
        return replace(profile, state=comparison_state or profile.state)
    return profile


def state_comparison(profile: TaxProfile, states: Iterable[str]) -> List[Dict[str, float | str]]:
    """Compare the same profile under the app's state income-tax proxies."""

    rows = []
    for state in states:
        result = estimate_tax(replace(profile, state=state))
        rows.append(
            {
                "state": state,
                "state_proxy_rate": STATE_PROXY_RATES.get(state, 0.04),
                "state_income_tax_proxy": result.state_income_tax_proxy,
                "estimated_take_home": result.take_home_after_estimated_tax,
            }
        )
    return sorted(rows, key=lambda row: float(row["estimated_take_home"]), reverse=True)

