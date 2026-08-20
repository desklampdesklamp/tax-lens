"""A compact one-page PDF tax-receipt generator."""

from __future__ import annotations

from io import BytesIO
from typing import Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from tax_engine import FILING_LABELS, TaxProfile, TaxResult


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _truncate(text: str, max_width: float, font: str, size: float) -> str:
    if stringWidth(text, font, size) <= max_width:
        return text
    ellipsis = "..."
    while text and stringWidth(text + ellipsis, font, size) > max_width:
        text = text[:-1]
    return text + ellipsis


def build_tax_receipt(
    profile: TaxProfile,
    result: TaxResult,
    allocations: Iterable[Mapping[str, object]],
) -> bytes:
    """Create an educational one-page receipt as PDF bytes."""

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 44
    cursor = height - 46

    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.rect(0, height - 84, width, 84, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin, height - 46, "Tax Lens: Estimated Tax Receipt")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(margin, height - 64, "Educational estimate for 2025 federal tax rules - not a tax return or filing advice")

    cursor -= 62
    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, cursor, "Profile snapshot")
    cursor -= 16
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9.5)
    profile_line = (
        f"{FILING_LABELS[profile.filing_status]} | {profile.state} | "
        f"W-2 wages: {_money(profile.salary)} | Dependents: {profile.dependents}"
    )
    pdf.drawString(margin, cursor, profile_line)

    cursor -= 30
    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, cursor, "Estimated tax summary")
    cursor -= 18

    summary = [
        ("Federal income tax", result.federal_income_tax),
        ("Social Security and Medicare", result.payroll_tax),
        ("State income-tax proxy", result.state_income_tax_proxy),
        ("Total estimated tax", result.total_estimated_tax),
        ("Estimated take-home after tax", result.take_home_after_estimated_tax),
    ]
    col_width = (width - 2 * margin) / 2
    for index, (label, value) in enumerate(summary):
        col = index % 2
        row = index // 2
        x = margin + col * col_width
        y = cursor - row * 24
        if index == 4:
            x = margin
            y = cursor - 2 * 24
        pdf.setFillColor(colors.HexColor("#4E6E81"))
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(x, y, label)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(x, y - 11, _money(value))

    cursor -= 103
    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, cursor, "Illustrative allocation of estimated federal income tax")
    cursor -= 13
    pdf.setFillColor(colors.HexColor("#4E6E81"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        margin,
        cursor,
        "This proportional model does not trace any taxpayer's payment to an agency or program.",
    )
    cursor -= 16

    rows = list(allocations)[:7]
    row_height = 17
    table_width = width - 2 * margin
    pdf.setFillColor(colors.HexColor("#EAF0F4"))
    pdf.rect(margin, cursor - 14, table_width, 15, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.drawString(margin + 6, cursor - 10, "Policy area")
    pdf.drawRightString(width - margin - 6, cursor - 10, "Illustrative amount")
    cursor -= 15
    for index, row in enumerate(rows):
        if index % 2 == 1:
            pdf.setFillColor(colors.HexColor("#F6F8FA"))
            pdf.rect(margin, cursor - 14, table_width, 15, fill=1, stroke=0)
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 8.5)
        label = _truncate(str(row["category"]), table_width - 150, "Helvetica", 8.5)
        pdf.drawString(margin + 6, cursor - 10, label)
        pdf.drawRightString(width - margin - 6, cursor - 10, _money(float(row["amount"])))
        cursor -= row_height

    cursor -= 9
    pdf.setFillColor(colors.HexColor("#113B5C"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin, cursor, "Important limitations")
    cursor -= 14
    pdf.setFillColor(colors.HexColor("#4E6E81"))
    pdf.setFont("Helvetica", 7.7)
    lines = [
        "Federal estimates simplify credits, deductions, and special situations. State figures are wage-income proxies.",
        "Budget categories are a dated FY2024 model. Appropriations, obligations, and outlays are different stages.",
        "See the app's Sources & Method tab before relying on this receipt for decisions.",
    ]
    for line in lines:
        pdf.drawString(margin, cursor, line)
        cursor -= 11

    pdf.setStrokeColor(colors.HexColor("#D9E2E9"))
    pdf.line(margin, 34, width - margin, 34)
    pdf.setFillColor(colors.HexColor("#617789"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margin, 22, "Tax Lens educational estimator | Generated locally in your browser session")
    pdf.drawRightString(width - margin, 22, "Tax year 2025")
    pdf.save()
    return buffer.getvalue()
