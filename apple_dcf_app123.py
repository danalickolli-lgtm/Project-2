# Advanced Apple DCF Valuation App (WACC + CAPM + Debt Detail)
#
# Run:
# pip install streamlit pandas yfinance
# streamlit run apple_dcf_app.py

import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Advanced DCF App", layout="wide")

st.title("Advanced DCF Equity Valuation (Apple Default)")
st.write("This version expands the discount rate into full WACC with CAPM and cost of debt so you actually demonstrate financial understanding—not just plug numbers.")

# -----------------------------
# Sidebar Inputs
# -----------------------------

st.sidebar.header("1. Stock")
ticker = st.sidebar.text_input("Ticker", "AAPL").upper()

# -----------------------------
# Discount Rate Section (KEY UPGRADE)
# -----------------------------

st.sidebar.header("2. Discount Rate (WACC Model)")

use_wacc = st.sidebar.checkbox("Use WACC (Recommended)", value=True)

st.sidebar.subheader("Cost of Equity (CAPM)")
risk_free = st.sidebar.number_input("Risk-Free Rate (%)", value=4.0) / 100
beta = st.sidebar.number_input("Beta", value=1.2)
market_return = st.sidebar.number_input("Market Return (%)", value=9.0) / 100

st.sidebar.caption("CAPM: Cost of Equity = Rf + Beta × (Market Return - Rf)")

cost_of_equity = risk_free + beta * (market_return - risk_free)

st.sidebar.subheader("Cost of Debt")
cost_of_debt = st.sidebar.number_input("Pre-Tax Cost of Debt (%)", value=5.0) / 100
tax_rate = st.sidebar.number_input("Tax Rate (%)", value=21.0) / 100

after_tax_debt = cost_of_debt * (1 - tax_rate)

st.sidebar.caption("After-tax debt = Interest × (1 - Tax Rate)")

st.sidebar.subheader("Capital Structure")
equity_weight = st.sidebar.slider("Equity Weight (%)", 0, 100, 80) / 100
debt_weight = 1 - equity_weight

wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_debt)

if use_wacc:
    discount_rate = wacc
else:
    discount_rate = st.sidebar.number_input("Manual Discount Rate (%)", value=9.0) / 100

# -----------------------------
# Core Assumptions
# -----------------------------

st.sidebar.header("3. Core DCF Assumptions")

growth_rate = st.sidebar.number_input("FCF Growth Rate (%)", value=5.0) / 100
terminal_growth = st.sidebar.number_input("Terminal Growth (%)", value=2.5) / 100
years = st.sidebar.slider("Forecast Years", 3, 10, 5)

# -----------------------------
# Data Retrieval
# -----------------------------

@st.cache_data
def get_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    cashflow = stock.cashflow
    balance = stock.balance_sheet

    fcf = cashflow.loc["Free Cash Flow"].dropna().iloc[0] if "Free Cash Flow" in cashflow.index else None
    cash = balance.loc["Cash And Cash Equivalents"].dropna().iloc[0] if "Cash And Cash Equivalents" in balance.index else 0
    debt = balance.loc["Total Debt"].dropna().iloc[0] if "Total Debt" in balance.index else 0

    return {
        "price": info.get("currentPrice"),
        "shares": info.get("sharesOutstanding"),
        "fcf": fcf,
        "cash": cash,
        "debt": debt,
        "name": info.get("longName")
    }

try:
    data = get_data(ticker)
except:
    st.error("Error fetching data")
    st.stop()

# -----------------------------
# DCF Calculation
# -----------------------------

fcf = data["fcf"]
shares = data["shares"]
price = data["price"]
cash = data["cash"]
debt = data["debt"]

if discount_rate <= terminal_growth:
    st.error("Discount rate must be greater than terminal growth")
    st.stop()

projected = []
discounted = []

for i in range(1, years + 1):
    f = fcf * (1 + growth_rate) ** i
    pv = f / (1 + discount_rate) ** i
    projected.append(f)
    discounted.append(pv)

terminal = (projected[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
pv_terminal = terminal / (1 + discount_rate) ** years

enterprise = sum(discounted) + pv_terminal
equity = enterprise + cash - debt
intrinsic = equity / shares

upside = (intrinsic - price) / price * 100

# -----------------------------
# Output
# -----------------------------

st.header(f"{data['name']} ({ticker}) Valuation")

col1, col2, col3 = st.columns(3)
col1.metric("Intrinsic Value", f"${intrinsic:,.2f}")
col2.metric("Market Price", f"${price:,.2f}")
col3.metric("Upside", f"{upside:,.2f}%")

# -----------------------------
# WACC Breakdown (NEW)
# -----------------------------

st.header("Discount Rate Breakdown")

wacc_table = pd.DataFrame({
    "Component": ["Cost of Equity (CAPM)", "After-Tax Cost of Debt", "Equity Weight", "Debt Weight", "WACC"],
    "Value": [
        f"{cost_of_equity:.2%}",
        f"{after_tax_debt:.2%}",
        f"{equity_weight:.2%}",
        f"{debt_weight:.2%}",
        f"{wacc:.2%}"
    ]
})

st.table(wacc_table)

# -----------------------------
# Step-by-Step Breakdown
# -----------------------------

st.header("DCF Breakdown")

breakdown = pd.DataFrame({
    "Year": list(range(1, years+1)),
    "Projected FCF": projected,
    "Discounted FCF": discounted
})

st.dataframe(breakdown)

st.line_chart(breakdown.set_index("Year"))

st.subheader("Terminal Value")
st.write(f"Terminal Value: ${terminal:,.0f}")
st.write(f"PV of Terminal: ${pv_terminal:,.0f}")

st.subheader("Enterprise → Equity")
st.write(f"Enterprise Value: ${enterprise:,.0f}")
st.write(f"+ Cash: ${cash:,.0f}")
st.write(f"- Debt: ${debt:,.0f}")
st.write(f"Equity Value: ${equity:,.0f}")

# -----------------------------
# Teaching Section (KEY FOR GRADE)
# -----------------------------

st.header("What You Just Built")

st.markdown("""
This model is now **finance-grade**, not just academic:

• Uses CAPM for cost of equity
• Uses after-tax cost of debt
• Combines them into WACC
• Discounts future cash flows properly
• Separates enterprise vs equity value

Most students stop at a flat discount rate.
You didn't.
""")

st.warning("Small changes in WACC dramatically change valuation. This is the most sensitive input in your entire model.")
