# Tax Lens

Tax Lens is an interactive Streamlit explainer for estimated 2025 U.S. federal income tax, employee payroll tax, rough state income tax, take-home pay, and federal-spending context.

## Features

- Federal income, Social Security, Medicare, and rough state-income-tax estimates
- Side-by-side scenario comparison for income, filing status, state, dependents, and pre-tax contributions
- Marginal-dollar explorer showing how much of additional wage income is kept
- Year-end federal withholding and per-paycheck course-correction estimate
- Personalized screening for retirement, HSA, dependent care, education, student-loan interest, Saver's Credit, and EITC opportunities
- Federal spending-category and agency-allocation explorers
- State-by-state comparison using the app's intentionally coarse income-tax proxies
- Anonymous downloadable PDF tax receipt
- Privacy-first inputs with no name, address, SSN, employer, or account details

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```bash
pytest -q
```

## Scope and sources

- Federal brackets and standard deductions: IRS Revenue Procedure 2024-40 for tax year 2025.
- Child Tax Credit: simplified nonrefundable application of the 2025 amount; refundable credit calculations are not included in the main estimate.
- Payroll tax: 6.2% employee Social Security tax up to the 2025 $176,100 wage base; 1.45% Medicare plus Additional Medicare Tax where applicable.
- Withholding projection: year-to-date federal withholding plus remaining paychecks multiplied by expected withholding per paycheck, following the structure described by the IRS Tax Withholding Estimator.
- Opportunity screens: IRS 2025 guidance for retirement limits, HSAs, education benefits, student-loan interest, dependent care, Saver's Credit, and EITC. Screens are leads, not eligibility determinations.
- Federal spending mix: broad categories based on Congressional Budget Office FY2024 outlays.
- Agency explorer: normalized FY2024 agency-level proxy shares based on Treasury/CBO context. Benefit payments and interest are grouped under their administering entities.
- Ukraine scale comparison: GAO's $174.2B figure for five FY2022-FY2024 supplemental appropriations, divided by roughly $19.15T in aggregate federal outlays for those years.

The state layer is a coarse effective-rate proxy, not a filing calculation. The app does not include refundable credits in its main estimate, capital-gains rates, AMT, self-employment tax, detailed phaseouts, local tax, ACA subsidies, or most state-specific rules. This project is educational and is not tax advice.
