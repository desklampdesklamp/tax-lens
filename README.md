# Tax Lens

Tax Lens is a Streamlit educational estimator for 2025 U.S. federal income tax,
employee payroll tax, a rough state-income-tax proxy, and federal spending
context. It is a planning and learning tool, not filing software or tax advice.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Included views

- Basic federal income-tax and employee payroll-tax estimate
- Pre-tax contribution, standard/itemized deduction, dependent, and state proxy inputs
- Scenario comparison, marginal-dollar explorer, withholding projection, opportunity prompts, and state comparison
- Downloadable, local-session PDF tax receipt
- Spending by policy area or major federal administrators
- Mandatory/discretionary/mixed spending filter, outlay trend, payroll-tax lane, agency role explorer, and public award-context link

## Key limitations

- The estimator is intentionally incomplete: it omits many credits, deductions,
  filing details, local taxes, and non-wage tax treatments.
- State estimates use rough effective-rate proxies and are not state tax returns.
- Spending allocations are a static FY2024 proportional illustration of estimated
  federal income tax, not a trace of individual tax dollars.

## Primary references

- [IRS Rev. Proc. 2024-40](https://www.irs.gov/pub/irs-irbs/irb24-45.pdf)
- [U.S. Treasury Fiscal Data — Federal Spending](https://fiscaldata.treasury.gov/americas-finance-guide/federal-spending/)
- [USAspending Agency Profiles](https://www.usaspending.gov/agency)
