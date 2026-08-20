"""Tax Lens — an educational, privacy-first U.S. tax and spending explorer."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from budget_data import (
    AGENCY_ALLOCATION_MODEL,
    FUNDING_FLOW,
    MISCONCEPTIONS,
    OUTLAY_TREND,
    REFERENCE_FISCAL_YEAR,
    SOURCES,
    SPENDING_CATEGORIES,
    illustrated_allocation,
)
from receipt import build_tax_receipt
from tax_engine import (
    FILING_LABELS,
    STATE_PROXY_RATES,
    TAX_YEAR,
    TaxProfile,
    estimate_marginal_dollar,
    estimate_tax,
    scenario_profile,
    state_comparison,
)


st.set_page_config(
    page_title="Tax Lens | Tax and spending explorer",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)


def money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def percent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def reset_inputs() -> None:
    defaults = {
        "salary": 75_000.0,
        "other_income": 0.0,
        "filing_status": "Single",
        "dependents": 0,
        "state": "California",
        "retirement": 0.0,
        "hsa": 0.0,
        "other_pretax": 0.0,
        "itemized": 0.0,
        "withholding_ytd": 0.0,
        "periods_completed": 0,
        "periods_per_year": 26,
    }
    for key, value in defaults.items():
        st.session_state[key] = value


def profile_from_sidebar() -> TaxProfile:
    status_labels = list(FILING_LABELS.values())
    label_to_key = {label: key for key, label in FILING_LABELS.items()}
    states = sorted(STATE_PROXY_RATES)

    with st.sidebar:
        st.header("Your estimate")
        st.caption("Enter rounded figures. Inputs stay in this browser session only.")
        salary = st.number_input(
            "Annual W-2 salary",
            min_value=0.0,
            value=75_000.0,
            step=1_000.0,
            key="salary",
        )
        other_income = st.number_input(
            "Other taxable income",
            min_value=0.0,
            value=0.0,
            step=1_000.0,
            help="For example, taxable interest, freelance income, or other income. This simple tool does not model self-employment tax.",
            key="other_income",
        )
        status_label = st.selectbox("Filing status", status_labels, key="filing_status")
        dependents = st.number_input("Qualifying dependents", min_value=0, value=0, step=1, key="dependents")
        state = st.selectbox("State", states, index=states.index("California"), key="state")

        st.divider()
        st.subheader("Pre-tax contributions")
        retirement = st.number_input("Traditional retirement contributions", min_value=0.0, value=0.0, step=500.0, key="retirement")
        hsa = st.number_input("HSA contributions", min_value=0.0, value=0.0, step=250.0, key="hsa")
        other_pretax = st.number_input("Other pre-tax deductions", min_value=0.0, value=0.0, step=250.0, key="other_pretax")
        itemized = st.number_input("Itemized deductions, if any", min_value=0.0, value=0.0, step=500.0, key="itemized")

        with st.expander("Withholding check", expanded=False):
            withholding_ytd = st.number_input("Federal + payroll + state withholding so far", min_value=0.0, value=0.0, step=100.0, key="withholding_ytd")
            periods_completed = st.number_input("Pay periods completed", min_value=0, max_value=366, value=0, step=1, key="periods_completed")
            periods_per_year = st.selectbox("Pay periods per year", [12, 24, 26, 52], index=2, key="periods_per_year")

        st.divider()
        if st.button("Clear session inputs", use_container_width=True):
            reset_inputs()
            st.rerun()
        st.caption("Tax Lens does not retain or transmit your entries.")

    return TaxProfile(
        salary=salary,
        other_income=other_income,
        filing_status=label_to_key[status_label],
        dependents=int(dependents),
        state=state,
        retirement_contributions=retirement,
        hsa_contributions=hsa,
        other_pretax=other_pretax,
        itemized_deductions=itemized,
        withholding_ytd=withholding_ytd,
        pay_periods_completed=int(periods_completed),
        pay_periods_per_year=int(periods_per_year),
    )


def tax_component_chart(result) -> go.Figure:
    values = {
        "Federal income tax": result.federal_income_tax,
        "Social Security": result.social_security_tax,
        "Medicare": result.medicare_tax + result.additional_medicare_tax,
        "State proxy": result.state_income_tax_proxy,
    }
    values = {name: amount for name, amount in values.items() if amount > 0}
    figure = px.pie(
        names=list(values),
        values=list(values.values()),
        hole=0.58,
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    figure.update_layout(
        margin=dict(l=8, r=8, t=8, b=8),
        legend_title_text="",
        annotations=[dict(text="Estimated<br>tax", x=0.5, y=0.5, showarrow=False, font_size=14)],
    )
    return figure


def render_tax_snapshot(profile: TaxProfile, result) -> None:
    st.subheader("Your estimated 2025 tax snapshot")
    st.caption("A planning estimate for W-2 wages and basic household inputs; it is not tax advice or a filing result.")

    metrics = st.columns(4)
    metrics[0].metric("Estimated total tax", money(result.total_estimated_tax))
    metrics[1].metric("Estimated take-home", money(result.take_home_after_estimated_tax))
    metrics[2].metric("Federal income tax", money(result.federal_income_tax), percent(result.effective_federal_rate))
    metrics[3].metric("Marginal federal rate", percent(result.marginal_federal_rate))

    left, right = st.columns((1.05, 0.95))
    with left:
        st.plotly_chart(tax_component_chart(result), use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown("#### Calculation summary")
        summary = pd.DataFrame(
            [
                ("Gross income", result.gross_income),
                ("Pre-tax contributions", -result.pretax_contributions),
                (f"{result.deduction_type} deduction", -result.deduction),
                ("Taxable income", result.taxable_income),
                ("Child tax credit estimate", -result.child_tax_credit),
            ],
            columns=["Item", "Amount"],
        )
        summary_display = summary.copy()
        summary_display["Amount"] = summary_display["Amount"].map(money)
        st.dataframe(summary_display, hide_index=True, use_container_width=True)
        st.info(
            f"The state figure is a rough wage-income proxy using a {STATE_PROXY_RATES.get(profile.state, 0.04):.1%} effective-rate assumption for {profile.state}. It excludes local taxes and state-specific credits."
        )

    with st.expander("See how your income fills federal brackets"):
        bracket_rows: List[Dict[str, object]] = []
        for row in result.bracket_rows:
            upper = "and above" if row["upper"] == float("inf") else money(row["upper"])
            bracket_rows.append(
                {
                    "Bracket range": f"{money(row['lower'])} to {upper}",
                    "Rate": f"{row['rate']:.0%}",
                    "Income taxed here": row["income_in_bracket"],
                    "Tax from this bracket": row["tax"],
                }
            )
        bracket_display = pd.DataFrame(bracket_rows)
        for column in ("Income taxed here", "Tax from this bracket"):
            bracket_display[column] = bracket_display[column].map(money)
        st.dataframe(bracket_display, hide_index=True, use_container_width=True)
        st.caption("Entering a higher bracket does not apply that rate to all of your income—only the portion inside that bracket.")


def render_planning_tools(profile: TaxProfile, result) -> None:
    st.subheader("Planning tools")
    scenario_tab, marginal_tab, withholding_tab, opportunity_tab, state_tab = st.tabs(
        ["Scenario comparison", "Marginal dollar", "Withholding", "Opportunities", "State comparison"]
    )

    with scenario_tab:
        comparison_state = st.selectbox(
            "Comparison state",
            sorted(STATE_PROXY_RATES),
            index=sorted(STATE_PROXY_RATES).index("Texas"),
            key="scenario_state",
        )
        scenario = st.selectbox(
            "What if…",
            [
                "Earn $10,000 more",
                "Contribute $5,000 more to retirement",
                "Add one dependent",
                "Move to comparison state",
            ],
            key="scenario_choice",
        )
        comparison_profile = scenario_profile(profile, scenario, comparison_state)
        comparison = estimate_tax(comparison_profile)
        cols = st.columns(3)
        cols[0].metric("Total estimated tax", money(comparison.total_estimated_tax), money(comparison.total_estimated_tax - result.total_estimated_tax))
        cols[1].metric("Estimated take-home", money(comparison.take_home_after_estimated_tax), money(comparison.take_home_after_estimated_tax - result.take_home_after_estimated_tax))
        cols[2].metric("Federal income tax", money(comparison.federal_income_tax), money(comparison.federal_income_tax - result.federal_income_tax))
        st.caption(f"Comparison: {scenario}. Everything else remains the same unless the scenario changes it.")

    with marginal_tab:
        additional_income = st.slider("Additional annual W-2 income", 1_000, 50_000, 10_000, 1_000, key="marginal_income")
        marginal = estimate_marginal_dollar(profile, float(additional_income))
        cols = st.columns(3)
        cols[0].metric("Additional income", money(marginal["additional_income"]))
        cols[1].metric("Estimated taxes on it", money(marginal["total_tax"]))
        cols[2].metric("You keep", money(marginal["take_home"]), percent(marginal["take_home"] / marginal["additional_income"]))
        breakdown = pd.DataFrame(
            [
                ("Federal income tax", marginal["federal_income_tax"]),
                ("Payroll tax", marginal["payroll_tax"]),
                ("State income-tax proxy", marginal["state_income_tax_proxy"]),
                ("Estimated take-home", marginal["take_home"]),
            ],
            columns=["Component", "Amount"],
        )
        chart = px.bar(breakdown, x="Amount", y="Component", orientation="h", color="Component", text="Amount", color_discrete_sequence=px.colors.qualitative.Safe)
        chart.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        chart.update_layout(showlegend=False, margin=dict(l=8, r=40, t=8, b=8), xaxis_title="Estimated dollars")
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
        st.caption("This is an estimate of the change from additional W-2 wage income, not a guarantee of net pay.")

    with withholding_tab:
        if result.projected_withholding is None:
            st.info("Enter withholding so far and completed pay periods in the sidebar to project a year-end withholding estimate.")
        else:
            projected = result.projected_withholding
            difference = result.projected_refund_or_amount_due or 0.0
            cols = st.columns(3)
            cols[0].metric("Projected year-end withholding", money(projected))
            cols[1].metric("Estimated annual tax", money(result.total_estimated_tax))
            label = "Projected refund" if difference >= 0 else "Projected amount due"
            cols[2].metric(label, money(abs(difference)))
            if difference < 0:
                remaining_periods = max(1, profile.pay_periods_per_year - profile.pay_periods_completed)
                st.warning(f"At this pace, the shortfall is about {money(abs(difference))}, or roughly {money(abs(difference) / remaining_periods)} per remaining pay period.")
            else:
                st.success("At this pace, projected withholding exceeds this simplified annual estimate.")
            st.caption("Projection assumes withholding per completed pay period stays constant. It does not replace an IRS withholding calculation.")

    with opportunity_tab:
        st.caption("These are prompts to investigate, not eligibility determinations or promised savings.")
        opportunities: List[Dict[str, str]] = []
        if profile.retirement_contributions < min(23_500.0, profile.salary):
            room = max(0.0, min(23_500.0, profile.salary) - profile.retirement_contributions)
            opportunities.append({"Topic": "Traditional retirement plan", "Why it may matter": f"You entered {money(profile.retirement_contributions)}. If your employer plan and circumstances allow, you may have up to about {money(room)} of additional 2025 deferral room before the base $23,500 limit."})
        if profile.hsa_contributions == 0:
            opportunities.append({"Topic": "Health Savings Account", "Why it may matter": "If you are HSA-eligible, contributions may have tax advantages. Eligibility and annual limits depend on your health-plan coverage."})
        if profile.dependents > 0:
            opportunities.append({"Topic": "Child and dependent care items", "Why it may matter": "Check whether child/dependent-care expenses, education costs, or related credits apply to your household."})
        if profile.salary + profile.other_income < 80_000:
            opportunities.append({"Topic": "Income-based credits", "Why it may matter": "Depending on family and filing facts, credits such as EITC, Saver's Credit, or education credits may be relevant. This estimator does not calculate eligibility."})
        if not opportunities:
            opportunities.append({"Topic": "Itemized deductions and credits", "Why it may matter": "Review specialized credits, retirement-plan rules, and state deductions with current official guidance or a qualified preparer."})
        st.dataframe(pd.DataFrame(opportunities), hide_index=True, use_container_width=True)

    with state_tab:
        suggestions = [profile.state, "Texas", "Florida", "New York", "California"]
        default_states = list(dict.fromkeys(suggestions))
        selected_states = st.multiselect(
            "States to compare",
            sorted(STATE_PROXY_RATES),
            default=default_states,
            key="state_comparison_states",
        )
        if selected_states:
            rows = state_comparison(profile, selected_states)
            frame = pd.DataFrame(rows)
            chart = px.bar(frame, x="state", y="estimated_take_home", color="state", text="estimated_take_home", color_discrete_sequence=px.colors.qualitative.Safe)
            chart.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            chart.update_layout(showlegend=False, yaxis_title="Estimated take-home", xaxis_title="", margin=dict(l=8, r=8, t=8, b=8))
            st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
            state_display = frame.copy()
            state_display["state_proxy_rate"] = state_display["state_proxy_rate"].map(lambda value: f"{value:.1%}")
            state_display["state_income_tax_proxy"] = state_display["state_income_tax_proxy"].map(money)
            state_display["estimated_take_home"] = state_display["estimated_take_home"].map(money)
            st.dataframe(state_display, hide_index=True, use_container_width=True)
        st.warning("State comparison uses a simple effective-rate proxy. It excludes local income, property, and sales taxes, and it is not a cost-of-living comparison.")


def allocation_frame(result, allocation_basis: str) -> pd.DataFrame:
    if allocation_basis == "Policy areas":
        frame = pd.DataFrame(SPENDING_CATEGORIES).rename(columns={"category": "Label", "detail": "Description"})
    else:
        frame = pd.DataFrame(AGENCY_ALLOCATION_MODEL).rename(columns={"agency": "Label", "role": "Description"})
        frame["kind"] = "Agency administration model"
    frame["Illustrative amount"] = frame["share"].apply(lambda share: illustrated_allocation(result.federal_income_tax, float(share)))
    return frame


def render_spending_and_agencies(profile: TaxProfile, result) -> List[Dict[str, object]]:
    st.subheader("Spending & agencies")
    st.caption("Explore a dated proportional model of your estimated federal income tax. It is not a map of where an individual payment goes.")
    st.info(
        "Federal revenues are pooled. These figures scale broad public-spending categories to your estimated federal income tax so the budget is easier to understand—not to claim that your dollars were routed to a particular agency."
    )

    allocation_basis = st.radio("View spending by", ["Policy areas", "Major administrators (agencies)"], horizontal=True, key="allocation_basis")
    frame = allocation_frame(result, allocation_basis)
    if allocation_basis == "Policy areas":
        kinds = st.multiselect(
            "Include spending types",
            ["Mandatory", "Discretionary", "Mixed"],
            default=["Mandatory", "Discretionary", "Mixed"],
            key="spending_types",
        )
        display_frame = frame[frame["kind"].isin(kinds)].copy()
    else:
        display_frame = frame.copy()

    left, right = st.columns((1, 1))
    with left:
        chart = px.pie(
            display_frame,
            values="Illustrative amount",
            names="Label",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        chart.update_layout(margin=dict(l=8, r=8, t=8, b=8), legend_title_text="")
        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})
    with right:
        visible_amount = float(display_frame["Illustrative amount"].sum())
        st.metric("Your estimated federal income tax", money(result.federal_income_tax))
        st.metric("Visible illustrative allocation", money(visible_amount), help="If you filtered categories, this is intentionally less than the total.")
        st.caption(f"Reference model: {REFERENCE_FISCAL_YEAR} broad federal spending context. Filtered categories remain shares of the full model, not renormalized shares.")
        if allocation_basis == "Major administrators (agencies)":
            st.warning("Agency and policy-area views are separate lenses. Do not add their totals together, and net interest is not represented as an agency allocation.")

    display_table = display_frame[["Label", "share", "kind", "Description", "Illustrative amount"]].sort_values("Illustrative amount", ascending=False)
    spending_display = display_table.copy()
    spending_display["share"] = spending_display["share"].map(lambda value: f"{value:.1f}%")
    spending_display["Illustrative amount"] = spending_display["Illustrative amount"].map(money)
    st.dataframe(spending_display, hide_index=True, use_container_width=True)

    if allocation_basis == "Major administrators (agencies)":
        selected_agency = st.selectbox("Inspect an agency role", frame["Label"].tolist(), key="agency_inspector")
        record = frame.loc[frame["Label"] == selected_agency].iloc[0]
        st.caption(f"**{selected_agency}:** {record['Description']}")

    st.markdown("#### Spending trend and tax lanes")
    trend, payroll = st.columns((1.25, 0.75))
    with trend:
        trend_frame = pd.DataFrame(OUTLAY_TREND)
        inflation_adjust = st.checkbox("Show rough 2024-dollar adjustment", value=False, key="inflation_adjust")
        if inflation_adjust:
            trend_frame["Displayed outlays"] = trend_frame["outlays_trillions"] * (1.03 / trend_frame["price_index"])
            title = "Rounded federal outlays, indexed to 2024 dollars"
        else:
            trend_frame["Displayed outlays"] = trend_frame["outlays_trillions"]
            title = "Rounded federal outlays, nominal dollars"
        # Fiscal years are discrete reporting periods, so use categorical labels
        # rather than a continuous numeric axis that can display half-years.
        trend_frame["Fiscal year"] = trend_frame["fiscal_year"].astype(int).astype(str)
        line = px.line(trend_frame, x="Fiscal year", y="Displayed outlays", markers=True, title=title)
        line.update_layout(yaxis_title="Trillions of dollars", xaxis_title="Fiscal year", margin=dict(l=8, r=8, t=38, b=8))
        st.plotly_chart(line, use_container_width=True, config={"displayModeBar": False})
    with payroll:
        lane_frame = pd.DataFrame(
            [
                ("Federal income tax", result.federal_income_tax, "General revenue illustration"),
                ("Social Security", result.social_security_tax, "Payroll-tax lane"),
                ("Medicare", result.medicare_tax + result.additional_medicare_tax, "Payroll-tax lane"),
            ],
            columns=["Component", "Estimated amount", "Context"],
        )
        lane_display = lane_frame.copy()
        lane_display["Estimated amount"] = lane_display["Estimated amount"].map(money)
        st.dataframe(lane_display, hide_index=True, use_container_width=True)
        st.caption("Payroll taxes are shown separately because they have distinct trust-fund financing roles. This is still an educational simplification.")

    st.markdown("#### Follow the money")
    flow_columns = st.columns(4)
    for column, (title, detail) in zip(flow_columns, FUNDING_FLOW):
        with column:
            st.markdown(f"**{title}**")
            st.caption(detail)

    with st.expander("Common misconceptions"):
        for item in MISCONCEPTIONS:
            st.markdown(f"**{item['myth']}**  \n{item['fact']}")

    st.markdown("#### Local award context")
    st.caption(
        f"To explore public award-recipient activity in {profile.state}, use USAspending's state profiles. Recipient location is not necessarily where work occurred, and this general state view is separate from the tax-allocation model."
    )
    st.link_button("Browse USAspending state profiles", "https://www.usaspending.gov/state")

    receipt_rows = (
        allocation_frame(result, "Policy areas")
        .rename(columns={"Label": "category", "Illustrative amount": "amount"})
        [["category", "amount"]]
        .sort_values("amount", ascending=False)
        .to_dict("records")
    )
    return receipt_rows


def render_sources_and_method(profile: TaxProfile, result, receipt_rows: List[Dict[str, object]]) -> None:
    st.subheader("Sources, method, and export")
    st.caption("The app is built to make assumptions inspectable. It does not make a payment-tracing claim.")

    method_col, source_col = st.columns((1, 1))
    with method_col:
        st.markdown("#### Estimation method")
        st.markdown(
            "- **Federal income tax:** 2025 ordinary-income brackets, standard deduction, and a limited Child Tax Credit estimate.\n"
            "- **Payroll tax:** employee Social Security and Medicare rates, including a simplified Additional Medicare calculation.\n"
            "- **State tax:** a deliberately rough effective-rate proxy; not a state return calculation.\n"
            "- **Spending views:** proportional illustrations based on estimated federal income tax, using a static FY2024 reference model."
        )
    with source_col:
        st.markdown("#### What to do before relying on it")
        st.markdown(
            "Use a current IRS calculator, filing software, or qualified tax professional for decisions or filing. Check the cited source pages for updates before relying on the spending context."
        )
        st.info("No profile fields are written to disk or sent to a server by this app.")

    source_frame = pd.DataFrame(SOURCES)
    st.dataframe(source_frame, hide_index=True, use_container_width=True)
    for item in SOURCES:
        st.link_button(f"Open: {item['source']}", str(item["url"]))

    receipt_pdf = build_tax_receipt(profile, result, receipt_rows)
    st.markdown("#### Download your educational tax receipt")
    st.download_button(
        "Download PDF receipt",
        data=receipt_pdf,
        file_name="tax-lens-estimated-tax-receipt.pdf",
        mime="application/pdf",
    )
    st.caption("The receipt is generated from the current browser-session inputs and contains the same limitations as the app.")


def main() -> None:
    st.title("Tax Lens")
    st.markdown("**Understand an estimated tax bill, then explore the public-spending context behind the numbers.**")
    st.caption(f"Tax year {TAX_YEAR} | Educational planning tool | No account required")

    profile = profile_from_sidebar()
    result = estimate_tax(profile)
    overview_tab, planning_tab, spending_tab, sources_tab = st.tabs(
        ["Tax snapshot", "Planning tools", "Spending & agencies", "Sources & export"]
    )

    with overview_tab:
        render_tax_snapshot(profile, result)
    with planning_tab:
        render_planning_tools(profile, result)
    with spending_tab:
        receipt_rows = render_spending_and_agencies(profile, result)
    with sources_tab:
        # Build again rather than relying on tab execution order.
        receipt_rows = allocation_frame(result, "Policy areas").rename(
            columns={"Label": "category", "Illustrative amount": "amount"}
        )[["category", "amount"]].sort_values("amount", ascending=False).to_dict("records")
        render_sources_and_method(profile, result, receipt_rows)


if __name__ == "__main__":
    main()
