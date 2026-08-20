import pandas as pd
import plotly.express as px
import streamlit as st

from receipt import build_tax_receipt
from tax_engine import (
    STATE_PROFILES,
    allocate_by_agency,
    allocate_federal_income_tax,
    calculate_estimate,
    incremental_tax_breakdown,
    opportunity_screen,
    project_withholding,
    ukraine_scale_estimate,
)


st.set_page_config(page_title="Tax Lens", page_icon="🧾", layout="wide")

COLORS = ["#1d4c3b", "#b46237", "#d8a14d", "#6b8578", "#8b6f47"]
FILING_STATUSES = ["Single", "Married filing jointly", "Head of household", "Married filing separately"]
PAY_PERIODS = {"Weekly (52)": 52, "Every two weeks (26)": 26, "Twice monthly (24)": 24, "Monthly (12)": 12}

st.markdown(
    """
    <style>
    .stApp {background: #f5f2ea; color: #16231d;}
    [data-testid="stHeader"] {background: rgba(245,242,234,.85);}
    .hero {padding: 2.4rem 2.6rem; border-radius: 28px; color: #f9f7f1;
      background: linear-gradient(125deg,#102c23 0%,#1d4c3b 62%,#b46237 145%);
      box-shadow: 0 18px 50px rgba(16,44,35,.13); margin-bottom: 1.3rem;}
    .eyebrow {font-size:.78rem; letter-spacing:.14em; text-transform:uppercase;
      color:#d8b993; font-weight:700;}
    .hero h1 {font-size:3.1rem; line-height:1.02; margin:.35rem 0 .7rem;}
    .hero p {max-width:760px;color:#dce8e1;font-size:1.08rem;}
    [data-testid="stMetric"] {background:#fffdf8;border:1px solid #ded9cd;
      padding:1rem 1.1rem;border-radius:18px;}
    div[data-testid="stForm"] {background:#fffdf8;border:1px solid #ded9cd;
      padding:1.2rem;border-radius:22px;}
    .note {background:#ebe5d8;border-radius:14px;padding:.85rem 1rem;color:#4c554f;}
    .feature {background:#fffdf8;border:1px solid #ded9cd;border-radius:18px;padding:1rem 1.1rem;margin:.35rem 0 .75rem;}
    .small {font-size:.86rem;color:#69736d;}
    </style>
    <div class="hero">
      <div class="eyebrow">A plain-English money explainer</div>
      <h1>See your taxes<br>in context.</h1>
      <p>Build a quick 2025 estimate, compare financial choices, check withholding, uncover potential tax breaks, and explore where federal money goes.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("tax_inputs"):
    st.subheader("Your household")
    c1, c2, c3 = st.columns(3)
    with c1:
        filing = st.selectbox("Filing status", FILING_STATUSES)
        salary = st.number_input("Your annual wages", min_value=0, value=75_000, step=1_000, format="%d")
        spouse_income = st.number_input("Spouse wages", min_value=0, value=0, step=1_000, format="%d", disabled=filing != "Married filing jointly")
        age = st.number_input("Your age", min_value=18, max_value=100, value=35, step=1)
    with c2:
        other_income = st.number_input("Other taxable income", min_value=0, value=0, step=500, help="Interest, bonuses, taxable gig income, etc.")
        dependents = st.number_input("Qualifying children", min_value=0, max_value=15, value=0, step=1, help="Used only as a preliminary screen; each credit has its own qualifying-child rules.")
        state = st.selectbox("State", sorted(STATE_PROFILES), index=sorted(STATE_PROFILES).index("California"))
        itemized = st.number_input("Itemized deductions", min_value=0, value=0, step=500, help="The estimator uses the larger of this amount or the standard deduction.")
    with c3:
        retirement = st.number_input("Pre-tax retirement contributions", min_value=0, value=0, step=500, help="Traditional 401(k), 403(b), TSP, or similar employee deferrals.")
        hsa_coverage = st.selectbox("HSA eligibility", ["Not eligible / unsure", "Self-only HDHP", "Family HDHP"])
        hsa_contributions = st.number_input("HSA contributions", min_value=0, value=0, step=250)
        other_pretax = st.number_input("Other pre-tax payroll deductions", min_value=0, value=0, step=250)

    with st.expander("Add details for personalized opportunities"):
        o1, o2, o3 = st.columns(3)
        with o1:
            dependent_care = st.number_input("Work-related dependent-care expenses", min_value=0, value=0, step=500)
        with o2:
            education_expenses = st.number_input("Qualified education expenses", min_value=0, value=0, step=500)
        with o3:
            student_loan_interest = st.number_input("Student-loan interest paid", min_value=0, value=0, step=100)

    with st.expander("Add paycheck information for the withholding checker"):
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            pay_frequency = st.selectbox("Pay frequency", list(PAY_PERIODS))
        with w2:
            withheld_ytd = st.number_input("Federal withholding year to date", min_value=0, value=0, step=250)
        with w3:
            paychecks_remaining = st.number_input("Paychecks remaining", min_value=0, max_value=52, value=0, step=1)
        with w4:
            future_withholding = st.number_input("Federal withholding per future paycheck", min_value=0, value=0, step=25)
        st.caption("Use federal income-tax withholding only—do not include Social Security, Medicare, state, or local withholding.")

    submitted = st.form_submit_button("Reveal my estimate", type="primary", use_container_width=True)

total_wages = salary + spouse_income
pretax_total = retirement + hsa_contributions + other_pretax
base_inputs = {
    "filing_status": filing,
    "wages": total_wages,
    "other_income": other_income,
    "pretax_contributions": pretax_total,
    "itemized_deductions": itemized,
    "qualifying_children": dependents,
    "state": state,
}
preliminary = calculate_estimate(**base_inputs)
withholding = project_withholding(preliminary["federal_income_tax"], withheld_ytd, paychecks_remaining, future_withholding)
result = calculate_estimate(**base_inputs, federal_withholding=withholding["projected_total_withholding"])

st.markdown("### Your snapshot")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Estimated total tax", f"${result['total_tax']:,.0f}")
m2.metric("Estimated take-home", f"${result['take_home']:,.0f}")
m3.metric("Effective tax rate", f"{result['effective_rate']:.1%}")
m4.metric(
    "Projected federal refund / due",
    f"${abs(result['refund_or_due']):,.0f}",
    "refund" if result["refund_or_due"] >= 0 else "due",
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Breakdown",
    "Scenario lab",
    "Withholding",
    "Opportunities",
    "Spending & agencies",
    "State comparison",
    "Tax receipt",
])

with tab1:
    left, right = st.columns([1.05, .95])
    components = pd.DataFrame({
        "Tax": ["Federal income", "Social Security", "Medicare", "State income (rough)"],
        "Amount": [result["federal_income_tax"], result["social_security"], result["medicare"], result["state_income_tax"]],
    })
    components = components[components.Amount > 0]
    if not components.empty:
        fig = px.pie(components, names="Tax", values="Amount", hole=.58, color_discrete_sequence=COLORS)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)")
        left.plotly_chart(fig, use_container_width=True)
    else:
        left.info("Enter income to see a tax breakdown.", icon="💡")
    with right:
        st.markdown("#### How the estimate was built")
        rows = {
            "Gross household income": result["gross_income"],
            "Pre-tax contributions": -result["pretax_contributions"],
            "Deduction used": -result["deduction_used"],
            "Federal taxable income": result["taxable_income"],
            "Federal tax before credits": result["federal_before_credits"],
            "Child tax credit used": -result["child_credit_used"],
        }
        for label, value in rows.items():
            st.write(f"**{label}**  ·  ${value:,.0f}")
        st.caption(f"Marginal federal bracket: {result['marginal_rate']:.0%} · State method: {result['state_note']}")

    st.markdown("#### Things you may not know")
    insights = []
    if result["deduction_used"] > itemized:
        insights.append(f"The standard deduction (${result['standard_deduction']:,.0f}) beats the itemized amount entered by ${result['standard_deduction'] - itemized:,.0f}.")
    else:
        insights.append(f"The itemized amount entered exceeds the standard deduction by ${itemized - result['standard_deduction']:,.0f}.")
    if pretax_total == 0 and result["gross_income"] > 0:
        insights.append("No pre-tax contributions were entered. Eligible retirement or HSA contributions may reduce federal taxable income.")
    if result["marginal_rate"] > result["federal_effective_rate"]:
        insights.append(f"Your {result['marginal_rate']:.0%} marginal bracket does not apply to every dollar. Your estimated effective federal income-tax rate is {result['federal_effective_rate']:.1%}.")
    for insight in insights:
        st.info(insight, icon="💡")

with tab2:
    st.markdown("#### Compare a second scenario")
    st.caption("Change a few levers and see both estimates side by side. The alternative uses the same other income and itemized deductions as your current case.")
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        alt_filing = st.selectbox("Alternative filing status", FILING_STATUSES, index=FILING_STATUSES.index(filing), key="alt_filing")
    with s2:
        alt_wages = st.number_input("Alternative household wages", min_value=0, value=int(total_wages), step=1_000, key="alt_wages")
    with s3:
        alt_state = st.selectbox("Alternative state", sorted(STATE_PROFILES), index=sorted(STATE_PROFILES).index(state), key="alt_state")
    with s4:
        alt_pretax = st.number_input("Alternative pre-tax total", min_value=0, value=int(pretax_total), step=500, key="alt_pretax")
    with s5:
        alt_children = st.number_input("Alternative children", min_value=0, max_value=15, value=int(dependents), step=1, key="alt_children")

    alt_result = calculate_estimate(
        filing_status=alt_filing,
        wages=alt_wages,
        other_income=other_income,
        pretax_contributions=alt_pretax,
        itemized_deductions=itemized,
        qualifying_children=alt_children,
        state=alt_state,
    )
    comparison = pd.DataFrame([
        ["Gross income", result["gross_income"], alt_result["gross_income"]],
        ["Federal income tax", result["federal_income_tax"], alt_result["federal_income_tax"]],
        ["Employee payroll tax", result["social_security"] + result["medicare"], alt_result["social_security"] + alt_result["medicare"]],
        ["State income tax (rough)", result["state_income_tax"], alt_result["state_income_tax"]],
        ["Total estimated tax", result["total_tax"], alt_result["total_tax"]],
        ["Take-home", result["take_home"], alt_result["take_home"]],
    ], columns=["Measure", "Current", "Alternative"])
    comparison["Change"] = comparison["Alternative"] - comparison["Current"]
    st.dataframe(
        comparison,
        hide_index=True,
        use_container_width=True,
        column_config={col: st.column_config.NumberColumn(format="$%.0f") for col in ["Current", "Alternative", "Change"]},
    )
    chart_df = comparison[comparison.Measure.isin(["Federal income tax", "Employee payroll tax", "State income tax (rough)"])].melt(id_vars="Measure", var_name="Scenario", value_name="Amount")
    chart_df = chart_df[chart_df.Scenario != "Change"]
    scenario_fig = px.bar(chart_df, x="Measure", y="Amount", color="Scenario", barmode="group", color_discrete_sequence=["#1d4c3b", "#b46237"])
    scenario_fig.update_layout(margin=dict(l=5, r=5, t=20, b=5), paper_bgcolor="rgba(0,0,0,0)", yaxis_tickprefix="$", yaxis_tickformat=",.0f")
    st.plotly_chart(scenario_fig, use_container_width=True)

    st.markdown("#### What if I earn more?")
    extra_income = st.slider("Additional wage income", min_value=1_000, max_value=50_000, value=5_000, step=1_000)
    incremental = incremental_tax_breakdown(base_inputs, extra_income)
    i1, i2, i3 = st.columns(3)
    i1.metric("Additional income", f"${extra_income:,.0f}")
    i2.metric("Estimated amount kept", f"${incremental['kept']:,.0f}")
    i3.metric("Combined incremental tax rate", f"{incremental['combined_incremental_rate']:.1%}")
    marginal_df = pd.DataFrame({
        "Destination": ["Amount kept", "Federal income tax", "Social Security", "Medicare", "State income (rough)"],
        "Amount": [incremental["kept"], incremental["federal_income_tax"], incremental["social_security"], incremental["medicare"], incremental["state_income_tax"]],
    })
    marginal_df = marginal_df[marginal_df.Amount > 0]
    marginal_fig = px.bar(marginal_df, x="Amount", y="Destination", orientation="h", color="Destination", color_discrete_sequence=COLORS)
    marginal_fig.update_layout(showlegend=False, margin=dict(l=5, r=10, t=20, b=5), paper_bgcolor="rgba(0,0,0,0)", xaxis_tickprefix="$", xaxis_tickformat=",.0f")
    st.plotly_chart(marginal_fig, use_container_width=True)

with tab3:
    st.markdown("#### Year-end withholding projection")
    st.markdown('<div class="note">This projects federal income-tax withholding as: year-to-date amount + remaining paychecks × future withholding per paycheck. Payroll and state taxes are separate.</div>', unsafe_allow_html=True)
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Estimated federal liability", f"${result['federal_income_tax']:,.0f}")
    w2.metric("Withheld so far", f"${withholding['withheld_year_to_date']:,.0f}")
    w3.metric("Projected future withholding", f"${withholding['projected_future_withholding']:,.0f}")
    w4.metric(f"Projected {withholding['status']}", f"${abs(withholding['projected_balance']):,.0f}")

    if paychecks_remaining:
        target = withholding["target_per_paycheck"]
        change = withholding["per_paycheck_adjustment"]
        st.markdown(f"At the current inputs, roughly **${target:,.0f} per remaining paycheck** would target a near-zero federal balance.")
        if change > 1:
            st.warning(f"That is about ${change:,.0f} more than the future per-paycheck withholding entered. A Form W-4 change may be worth reviewing.", icon="⚠️")
        elif change < -1:
            st.info(f"That is about ${abs(change):,.0f} less than the future per-paycheck withholding entered. You may be on track for a refund.", icon="💡")
        else:
            st.success("The entered future withholding is close to this simplified target.", icon="✅")
    else:
        st.info("Enter remaining paychecks and future per-paycheck withholding in the household form to calculate a course correction.", icon="💡")

    annual_periods = PAY_PERIODS[pay_frequency]
    p1, p2, p3 = st.columns(3)
    p1.metric("Gross per paycheck", f"${total_wages / annual_periods:,.0f}")
    p2.metric("Average tax per paycheck", f"${result['total_tax'] / annual_periods:,.0f}")
    p3.metric("Estimated take-home per paycheck", f"${result['take_home'] / annual_periods:,.0f}")
    st.caption("The per-paycheck figures spread annual totals evenly and will not exactly match payroll software. For a filing-grade recommendation, use the IRS Tax Withholding Estimator.")

with tab4:
    st.markdown("#### Personalized opportunity screen")
    st.markdown('<div class="note">These are leads to investigate, not confirmed eligibility or amounts. Estimates can overlap, so do not add them together.</div>', unsafe_allow_html=True)
    opportunities = opportunity_screen(
        filing_status=filing,
        gross_income=result["gross_income"],
        earned_income=total_wages,
        marginal_rate=result["marginal_rate"],
        qualifying_children=dependents,
        age=age,
        retirement_contributions=retirement,
        hsa_coverage=hsa_coverage,
        hsa_contributions=hsa_contributions,
        dependent_care_expenses=dependent_care,
        education_expenses=education_expenses,
        student_loan_interest=student_loan_interest,
    )
    if not opportunities:
        st.info("Add income or optional expense details to generate opportunity leads.", icon="💡")
    for opportunity in opportunities:
        with st.expander(f"{opportunity['title']} · illustrative amount ${opportunity['estimate']:,.0f}"):
            st.write(opportunity["detail"])
            st.markdown(f"**Next check:** {opportunity['next_step']}")
    st.caption("The opportunity screen does not calculate refundable credits in the main tax estimate; it keeps uncertain eligibility from being treated as guaranteed savings.")

with tab5:
    category_tab, agency_tab, conflict_tab = st.tabs(["Spending categories", "Agency explorer", "Conflict context"])
    with category_tab:
        st.markdown("#### An illustrative allocation—not a receipt")
        st.markdown('<div class="note">Federal dollars are pooled. This applies broad FY2024 federal outlay shares to estimated federal income tax only; it cannot trace actual dollars.</div>', unsafe_allow_html=True)
        allocation = allocate_federal_income_tax(result["federal_income_tax"])
        alloc_df = pd.DataFrame(allocation, columns=["Category", "Estimated share"])
        fig2 = px.bar(alloc_df.sort_values("Estimated share"), x="Estimated share", y="Category", orientation="h", color="Category", color_discrete_sequence=px.colors.qualitative.Safe)
        fig2.update_layout(showlegend=False, margin=dict(l=5, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", xaxis_tickprefix="$", xaxis_tickformat=",.0f")
        st.plotly_chart(fig2, use_container_width=True)
    with agency_tab:
        st.markdown("#### Estimated share by federal agency")
        agency = pd.DataFrame(allocate_by_agency(result["federal_income_tax"]), columns=["Agency", "Estimated share"]).sort_values("Estimated share", ascending=False)
        a1, a2 = st.columns([1.3, .7])
        with a1:
            fig3 = px.bar(agency.sort_values("Estimated share"), x="Estimated share", y="Agency", orientation="h", color="Estimated share", color_continuous_scale=["#d8b993", "#b46237", "#1d4c3b"])
            fig3.update_layout(coloraxis_showscale=False, margin=dict(l=5, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", xaxis_tickprefix="$", xaxis_tickformat=",.0f")
            st.plotly_chart(fig3, use_container_width=True)
        with a2:
            selected_agency = st.selectbox("Inspect an agency", agency["Agency"].tolist())
            selected_amount = agency.loc[agency["Agency"] == selected_agency, "Estimated share"].iloc[0]
            st.metric("Illustrative amount", f"${selected_amount:,.0f}")
            st.write(f"About **{selected_amount / result['federal_income_tax']:.1%}** of estimated federal income tax." if result["federal_income_tax"] else "No federal income tax was estimated from the current inputs.")
            st.caption("Payroll taxes are excluded because Social Security and Medicare have dedicated financing streams and appear separately.")
        with st.expander("See the full agency table"):
            display_agency = agency.copy()
            display_agency["Share of federal income tax"] = display_agency["Estimated share"] / max(result["federal_income_tax"], 1) * 100
            st.dataframe(display_agency, hide_index=True, use_container_width=True, column_config={"Estimated share": st.column_config.NumberColumn(format="$%.0f"), "Share of federal income tax": st.column_config.NumberColumn(format="%.1f%%")})
    with conflict_tab:
        st.markdown("#### Ukraine-related appropriations scale")
        war_scale = ukraine_scale_estimate(result["federal_income_tax"])
        st.metric("Historical scale estimate", f"about ${war_scale:,.0f}")
        st.caption("Estimated federal income tax × $174.2B in Ukraine-related appropriations for FY2022–FY2024 ÷ aggregate federal outlays over those years. Appropriations are not the same as annual spending, direct aid, or a traceable contribution.")

with tab6:
    st.markdown("#### Compare the same household across states")
    st.markdown('<div class="note">Only the app\'s rough state income-tax proxy changes here. Sales, property, local, business, and consumption taxes—and cost of living—are not included.</div>', unsafe_allow_html=True)
    state_rows = []
    for candidate in sorted(STATE_PROFILES):
        candidate_result = calculate_estimate(**{**base_inputs, "state": candidate})
        state_rows.append({
            "State": candidate,
            "State income-tax proxy": candidate_result["state_income_tax"],
            "Total estimated tax": candidate_result["total_tax"],
            "Estimated take-home": candidate_result["take_home"],
            "Difference vs current": candidate_result["take_home"] - result["take_home"],
        })
    states_df = pd.DataFrame(state_rows).sort_values(["State income-tax proxy", "State"])
    current_rank = states_df.reset_index(drop=True).index[states_df.reset_index(drop=True).State == state][0] + 1
    sr1, sr2, sr3 = st.columns(3)
    sr1.metric("Current state proxy", f"${result['state_income_tax']:,.0f}")
    sr2.metric("Current proxy rank", f"{current_rank} of {len(states_df)}", help="Lowest estimated state-income-tax proxy ranks first; ties are alphabetical.")
    sr3.metric("States with no broad wage tax", f"{sum(STATE_PROFILES[s] == 0 for s in STATE_PROFILES)}")

    default_states = list(dict.fromkeys([state, "Texas", "Florida", "New York", "California"]))
    selected_states = st.multiselect("States to chart", sorted(STATE_PROFILES), default=default_states)
    selected_df = states_df[states_df.State.isin(selected_states)]
    if not selected_df.empty:
        state_fig = px.bar(selected_df.sort_values("State income-tax proxy"), x="State", y="State income-tax proxy", color="State income-tax proxy", color_continuous_scale=["#d8b993", "#b46237", "#1d4c3b"])
        state_fig.update_layout(coloraxis_showscale=False, margin=dict(l=5, r=10, t=20, b=5), paper_bgcolor="rgba(0,0,0,0)", yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(state_fig, use_container_width=True)
    with st.expander("See all states"):
        st.dataframe(states_df, hide_index=True, use_container_width=True, column_config={col: st.column_config.NumberColumn(format="$%.0f") for col in ["State income-tax proxy", "Total estimated tax", "Estimated take-home", "Difference vs current"]})

with tab7:
    st.markdown("#### Download your anonymous tax receipt")
    r1, r2 = st.columns([1, 1])
    with r1:
        receipt_bytes = build_tax_receipt(result, filing, state)
        st.download_button(
            "Download PDF tax receipt",
            data=receipt_bytes,
            file_name="tax-lens-2025-receipt.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        st.caption("The PDF includes your estimate, tax components, federal spending categories, and largest agency-scale allocations.")
    with r2:
        st.markdown("**Privacy-first by design**")
        st.write("The form does not ask for your name, address, Social Security number, employer, or account information. This app code does not write entries to a database or local file. Your hosting provider may still process session data under its own policy.")
        if st.button("Clear my information", use_container_width=True):
            st.session_state.clear()
            st.rerun()

st.divider()
st.markdown(
    "**Official references:** [IRS 2025 inflation adjustments](https://www.irs.gov/irb/2024-45_IRB), "
    "[IRS withholding guidance](https://www.irs.gov/individuals/tax-withholding-estimator-faqs), "
    "[IRS HSA guidance](https://www.irs.gov/publications/p969), "
    "[IRS education benefits](https://www.irs.gov/publications/p970), and "
    "[IRS retirement limits](https://www.irs.gov/newsroom/401k-limit-increases-to-23500-for-2025-ira-limit-remains-7000)."
)
st.caption("Educational estimate for tax year 2025. Not tax, legal, or financial advice. State tax is intentionally approximate. The main estimate excludes refundable credits, capital-gains rates, AMT, self-employment tax, detailed phaseouts, local taxes, ACA subsidies, and many state-specific rules. Spending context: CBO and Treasury FY2024; conflict context: GAO Ukraine oversight.")
