"""Build a compact, anonymous PDF tax receipt for Tax Lens."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from tax_engine import allocate_by_agency, allocate_federal_income_tax


def _money(value: float) -> str:
    return f"${value:,.0f}"


def build_tax_receipt(result: dict, filing_status: str, state: str) -> bytes:
    """Return a one-to-two-page PDF containing no direct identifiers."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=.52 * inch,
        leftMargin=.52 * inch,
        topMargin=.38 * inch,
        bottomMargin=.38 * inch,
        title="Tax Lens 2025 Estimate",
        author="Tax Lens",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReceiptTitle", parent=styles["Title"], textColor=colors.HexColor("#12372b"), alignment=TA_CENTER, fontSize=21, leading=23, spaceAfter=2))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["BodyText"], textColor=colors.HexColor("#56635d"), alignment=TA_CENTER, fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#12372b"), fontSize=10.5, leading=12, spaceBefore=5, spaceAfter=3))
    styles.add(ParagraphStyle(name="Fine", parent=styles["BodyText"], textColor=colors.HexColor("#56635d"), fontSize=7.2, leading=8.5))

    story = [
        Paragraph("Tax Lens", styles["ReceiptTitle"]),
        Paragraph("Educational 2025 tax estimate and spending context", styles["Subtitle"]),
        Spacer(1, 7),
    ]

    summary_data = [
        ["Household profile", f"{filing_status} · {state}"],
        ["Gross household income", _money(result["gross_income"])],
        ["Federal taxable income", _money(result["taxable_income"])],
        ["Estimated total tax", _money(result["total_tax"])],
        ["Estimated take-home", _money(result["take_home"])],
        ["Effective tax rate", f"{result['effective_rate']:.1%}"],
    ]
    summary = Table(summary_data, colWidths=[2.35 * inch, 4.25 * inch])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3efe5")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#56635d")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#12372b")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#d9d3c5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([summary, Paragraph("Estimated tax breakdown", styles["Section"])])

    tax_rows = [["Federal income", _money(result["federal_income_tax"])], ["Social Security", _money(result["social_security"])], ["Medicare", _money(result["medicare"])], ["State income (rough)", _money(result["state_income_tax"])]]
    taxes = Table(tax_rows, colWidths=[3.3 * inch, 3.3 * inch])
    taxes.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), .25, colors.HexColor("#ded9cd")), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([taxes, Paragraph("Illustrative federal spending allocation", styles["Section"])])

    spending = sorted(allocate_federal_income_tax(result["federal_income_tax"]), key=lambda row: row[1], reverse=True)[:8]
    spending_rows = [[category, _money(amount)] for category, amount in spending]
    spending_table = Table(spending_rows, colWidths=[4.5 * inch, 2.1 * inch])
    spending_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), .2, colors.HexColor("#e2ddd2")), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([spending_table, Paragraph("Largest agency-scale allocations", styles["Section"])])

    agencies = sorted(allocate_by_agency(result["federal_income_tax"]), key=lambda row: row[1], reverse=True)[:6]
    agency_rows = [[agency, _money(amount)] for agency, amount in agencies]
    agency_table = Table(agency_rows, colWidths=[4.5 * inch, 2.1 * inch])
    agency_table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), .2, colors.HexColor("#e2ddd2")), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([
        agency_table,
        Spacer(1, 5),
        Paragraph("Federal dollars are pooled. Spending and agency figures apply broad FY2024 outlay shares to estimated federal income tax; they are not traceable personal contributions. State tax is a coarse proxy. This receipt excludes many tax provisions and is not tax, legal, or financial advice.", styles["Fine"]),
        Spacer(1, 4),
        Paragraph("Federal assumptions: IRS 2025 brackets, standard deductions, payroll rules, and Child Tax Credit guidance. Spending context: CBO and U.S. Treasury FY2024.", styles["Fine"]),
    ])
    doc.build(story)
    return buffer.getvalue()
