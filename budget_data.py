"""Transparent, dated reference data for the Spending & Agencies explorer.

Figures in this file are intentionally packaged as an educational model rather
than as a real-time government ledger. Every chart in the app labels its fiscal
year and source, and distinguishes high-level spending context from an
individual's proportional illustration.
"""

from __future__ import annotations

from typing import Dict, List


REFERENCE_FISCAL_YEAR = "FY2024"


# Rounded policy-area shares used only to make an individual allocation legible.
# They sum to 100 and are not meant to recreate every budget account.
SPENDING_CATEGORIES: List[Dict[str, object]] = [
    {"category": "Social Security", "share": 21.0, "kind": "Mandatory", "detail": "Retirement, survivor, and disability benefits"},
    {"category": "Medicare", "share": 15.0, "kind": "Mandatory", "detail": "Health coverage for eligible people"},
    {"category": "Health", "share": 10.0, "kind": "Mixed", "detail": "Medicaid, public health, and other health programs"},
    {"category": "Income security", "share": 9.0, "kind": "Mandatory", "detail": "Income support, nutrition, housing, and related programs"},
    {"category": "National defense", "share": 12.0, "kind": "Discretionary", "detail": "Military personnel, operations, procurement, and research"},
    {"category": "Veterans' benefits and services", "share": 5.0, "kind": "Mixed", "detail": "Health care, compensation, pensions, and benefits"},
    {"category": "Net interest", "share": 13.0, "kind": "Mandatory", "detail": "Interest on federal debt; not an agency program"},
    {"category": "Education", "share": 3.0, "kind": "Mixed", "detail": "Student aid and education programs"},
    {"category": "Transportation", "share": 2.0, "kind": "Mixed", "detail": "Highways, transit, aviation, rail, and safety"},
    {"category": "International affairs", "share": 1.0, "kind": "Discretionary", "detail": "Diplomacy, development, and foreign assistance"},
    {"category": "Science and space", "share": 1.0, "kind": "Discretionary", "detail": "Research, weather, and space programs"},
    {"category": "General government", "share": 1.0, "kind": "Mixed", "detail": "Justice, homeland security, and general administration"},
    {"category": "Other programs", "share": 7.0, "kind": "Mixed", "detail": "All other functions in this simplified model"},
]


# A distinct, high-level administration view.  This is not a reconciliation to
# budget functions and should never be added to SPENDING_CATEGORIES.
AGENCY_ALLOCATION_MODEL: List[Dict[str, object]] = [
    {"agency": "Social Security Administration", "share": 24.0, "role": "Administers Social Security benefits"},
    {"agency": "HHS and CMS", "share": 22.0, "role": "Administers Medicare, Medicaid, and public-health programs"},
    {"agency": "Department of Defense", "share": 17.0, "role": "Military operations, procurement, and readiness"},
    {"agency": "Department of Veterans Affairs", "share": 8.0, "role": "Veterans' health care and benefits"},
    {"agency": "Department of Agriculture", "share": 6.0, "role": "Nutrition, agriculture, and rural programs"},
    {"agency": "Department of the Treasury", "share": 5.0, "role": "Tax administration and federal financial operations"},
    {"agency": "Department of Education", "share": 4.0, "role": "Student aid and education programs"},
    {"agency": "Department of Homeland Security", "share": 4.0, "role": "Border, transportation, and emergency security functions"},
    {"agency": "Department of Transportation", "share": 3.0, "role": "Transportation grants, safety, and infrastructure"},
    {"agency": "Department of State and foreign assistance", "share": 2.0, "role": "Diplomacy and selected foreign-assistance programs"},
    {"agency": "NASA and NSF", "share": 2.0, "role": "Civil space and scientific research"},
    {"agency": "Department of Justice", "share": 1.0, "role": "Federal law enforcement and justice programs"},
    {"agency": "Environmental Protection Agency", "share": 0.5, "role": "Environmental protection and grants"},
    {"agency": "Department of Housing and Urban Development", "share": 1.5, "role": "Housing assistance and community development"},
]


# Rounded historical outlay series, shown as a context trend instead of a claim
# about an individual's actual allocation.
OUTLAY_TREND: List[Dict[str, float | int]] = [
    {"fiscal_year": 2020, "outlays_trillions": 6.55, "price_index": 0.88},
    {"fiscal_year": 2021, "outlays_trillions": 6.82, "price_index": 0.93},
    {"fiscal_year": 2022, "outlays_trillions": 6.27, "price_index": 0.97},
    {"fiscal_year": 2023, "outlays_trillions": 6.16, "price_index": 1.00},
    {"fiscal_year": 2024, "outlays_trillions": 6.75, "price_index": 1.03},
]


FUNDING_FLOW = [
    ("1. Revenue", "Income taxes, payroll taxes, borrowing, and other receipts finance the federal government as a whole."),
    ("2. Budget authority", "Congress enacts laws that make funds available for specified purposes."),
    ("3. Obligation", "An agency commits money through a grant, contract, benefit, or other legal action."),
    ("4. Outlay", "The Treasury makes a payment. Outlays are often later than appropriations and obligations."),
]


MISCONCEPTIONS = [
    {
        "myth": "My specific tax payment is routed to one agency.",
        "fact": "Federal revenues are pooled. This app uses proportional illustrations, not a payment-tracing claim.",
    },
    {
        "myth": "An appropriation means the money was spent immediately.",
        "fact": "Appropriations, obligations, and outlays are different stages and can occur in different fiscal years.",
    },
    {
        "myth": "Federal income tax and payroll tax fund the same things in the same way.",
        "fact": "They are presented separately here because payroll taxes have distinct trust-fund financing roles.",
    },
]


SOURCES = [
    {
        "source": "U.S. Treasury Fiscal Data — Federal Spending",
        "use": "Federal-spending context; explains the outlay lens",
        "url": "https://fiscaldata.treasury.gov/americas-finance-guide/federal-spending/",
        "as_of": "Reference page accessed August 2026",
    },
    {
        "source": "USAspending Agency Profiles",
        "use": "Agency obligation and outlay context; recipient and award exploration",
        "url": "https://www.usaspending.gov/agency",
        "as_of": "Reference page accessed August 2026",
    },
    {
        "source": "IRS Rev. Proc. 2024-40",
        "use": "2025 federal income-tax brackets and standard deduction inputs",
        "url": "https://www.irs.gov/pub/irs-irbs/irb24-45.pdf",
        "as_of": "Published November 2024",
    },
]


def illustrated_allocation(user_federal_income_tax: float, share_percent: float) -> float:
    """Return a proportional *illustration*, never a claim of tax tracing."""

    return max(0.0, user_federal_income_tax) * max(0.0, share_percent) / 100.0


