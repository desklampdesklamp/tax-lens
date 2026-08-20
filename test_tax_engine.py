from receipt import build_tax_receipt
from tax_engine import (
    allocate_by_agency,
    allocate_federal_income_tax,
    calculate_estimate,
    incremental_tax_breakdown,
    opportunity_screen,
    project_withholding,
    student_loan_interest_deduction,
)


def base_inputs(**overrides):
    inputs = {
        "filing_status": "Single",
        "wages": 75_000,
        "other_income": 0,
        "pretax_contributions": 0,
        "itemized_deductions": 0,
        "qualifying_children": 0,
        "state": "Texas",
    }
    inputs.update(overrides)
    return inputs


def test_zero_income():
    result = calculate_estimate(**base_inputs(wages=0))
    assert result["total_tax"] == 0
    assert result["take_home"] == 0


def test_single_75k():
    result = calculate_estimate(**base_inputs())
    assert round(result["taxable_income"]) == 60_000
    assert round(result["federal_income_tax"]) == 8_114
    assert result["marginal_rate"] == .22


def test_2025_child_credit_is_applied():
    without_child = calculate_estimate(**base_inputs())
    with_child = calculate_estimate(**base_inputs(qualifying_children=1))
    assert round(without_child["federal_income_tax"] - with_child["federal_income_tax"]) == 2_200


def test_withholding_projection_and_target():
    projection = project_withholding(8_000, 4_000, 10, 300)
    assert projection["projected_total_withholding"] == 7_000
    assert projection["projected_balance"] == -1_000
    assert projection["target_per_paycheck"] == 400
    assert projection["per_paycheck_adjustment"] == 100
    assert projection["status"] == "amount due"


def test_incremental_breakdown_reconciles_to_extra_income():
    incremental = incremental_tax_breakdown(base_inputs(), 5_000)
    pieces = incremental["kept"] + incremental["federal_income_tax"] + incremental["social_security"] + incremental["medicare"] + incremental["state_income_tax"]
    assert abs(pieces - 5_000) < .01
    assert 0 < incremental["combined_incremental_rate"] < 1


def test_student_loan_interest_phaseout():
    assert student_loan_interest_deduction("Single", 80_000, 3_000) == 2_500
    assert round(student_loan_interest_deduction("Single", 90_000, 2_500), 2) == 1_666.67
    assert student_loan_interest_deduction("Single", 100_000, 2_500) == 0
    assert student_loan_interest_deduction("Married filing separately", 50_000, 2_500) == 0


def test_opportunity_screen_returns_personalized_leads():
    result = calculate_estimate(**base_inputs(wages=55_000, qualifying_children=1))
    opportunities = opportunity_screen(
        filing_status="Single",
        gross_income=result["gross_income"],
        earned_income=55_000,
        marginal_rate=result["marginal_rate"],
        qualifying_children=1,
        age=35,
        retirement_contributions=1_000,
        hsa_coverage="Self-only HDHP",
        hsa_contributions=500,
        dependent_care_expenses=3_000,
        education_expenses=4_000,
        student_loan_interest=1_000,
    )
    titles = {item["title"] for item in opportunities}
    assert "Workplace retirement contribution" in titles
    assert "Health Savings Account" in titles
    assert "Child and dependent care credit" in titles
    assert "Education credit" in titles
    assert "Student-loan interest deduction" in titles


def test_allocations_sum_to_federal_tax():
    assert abs(sum(value for _, value in allocate_federal_income_tax(1_000)) - 1_000) < .01
    assert abs(sum(value for _, value in allocate_by_agency(1_000)) - 1_000) < .01


def test_pdf_receipt_is_valid_pdf_bytes():
    result = calculate_estimate(**base_inputs())
    pdf = build_tax_receipt(result, "Single", "Texas")
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 2_000
