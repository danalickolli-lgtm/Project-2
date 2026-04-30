# Apple Stock DCF Equity Valuation App
# Python Streamlit Version
#
# How to run:
# 1. Install required packages:
#    pip install streamlit pandas yfinance
#
# 2. Save this file as:
#    apple_dcf_app.py
#
# 3. Run in Terminal:
#    streamlit run apple_dcf_app.py

import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Apple DCF Valuation App", layout="wide")

st.title("Apple Stock DCF Equity Valuation App")
st.write(
    "This app estimates the intrinsic value of Apple stock using a Discounted Cash Flow model. "
    "Users can change the ticker and valuation assumptions, while some market data is retrieved automatically."
)

# ------------------------------------------------------------
# Sidebar Inputs
# ------------------------------------------------------------

st.sidebar.header("1. Stock Selection")

ticker = st.sidebar.text_input("Stock Ticker", "AAPL").upper()

st.sidebar.caption(
    "Enter the ticker symbol of the company you want to value. "
    "For this project, Apple is used as the default example."
)

st.sidebar.header("2. Valuation Assumptions")

growth_rate = st.sidebar.number_input(
    "Annual Free Cash Flow Growth Rate (%)",
    min_value=-20.0,
    max_value=30.0,
    value=5.0,
    step=0.5,
) / 100

st.sidebar.caption(
    "This estimates how fast the company's free cash flow will grow each year during the forecast period. "
    "A mature company like Apple usually should not be given an extremely high long-term growth rate."
)

discount_rate = st.sidebar.number_input(
    "Discount Rate / Required Return (%)",
    min_value=1.0,
    max_value=25.0,
    value=9.0,
    step=0.5,
) / 100

st.sidebar.caption(
    "The discount rate represents the investor's required rate of return. "
    "A higher discount rate lowers the present value of future cash flows."
)

terminal_growth_rate = st.sidebar.number_input(
    "Terminal Growth Rate (%)",
    min_value=0.0,
    max_value=6.0,
    value=2.5,
    step=0.25,
) / 100

st.sidebar.caption(
    "The terminal growth rate estimates the company's long-term growth after the forecast period. "
    "This should usually be conservative and below the discount rate."
)

forecast_years = st.sidebar.slider(
    "Forecast Period in Years",
    min_value=3,
    max_value=10,
    value=5,
)

st.sidebar.caption(
    "This controls how many years of free cash flow are explicitly forecasted before terminal value is calculated."
)

st.sidebar.header("3. Optional Manual Overrides")

use_manual_fcf = st.sidebar.checkbox("Manually enter free cash flow instead of using online data", value=False)
manual_fcf = st.sidebar.number_input(
    "Manual Current Free Cash Flow ($ billions)",
    min_value=0.01,
    value=100.0,
    step=1.0,
)

use_manual_shares = st.sidebar.checkbox("Manually enter shares outstanding instead of using online data", value=False)
manual_shares = st.sidebar.number_input(
    "Manual Shares Outstanding (billions)",
    min_value=0.01,
    value=15.0,
    step=0.1,
)

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info

    cashflow = stock.cashflow
    balance_sheet = stock.balance_sheet

    current_price = info.get("currentPrice", None)
    shares_outstanding = info.get("sharesOutstanding", None)
    company_name = info.get("longName", ticker_symbol)

    free_cash_flow = None
    cash = 0
    debt = 0

    try:
        if "Free Cash Flow" in cashflow.index:
            free_cash_flow = cashflow.loc["Free Cash Flow"].dropna().iloc[0]
    except Exception:
        free_cash_flow = None

    try:
        if "Cash And Cash Equivalents" in balance_sheet.index:
            cash = balance_sheet.loc["Cash And Cash Equivalents"].dropna().iloc[0]
    except Exception:
        cash = 0

    try:
        if "Total Debt" in balance_sheet.index:
            debt = balance_sheet.loc["Total Debt"].dropna().iloc[0]
    except Exception:
        debt = 0

    return {
        "company_name": company_name,
        "current_price": current_price,
        "shares_outstanding": shares_outstanding,
        "free_cash_flow": free_cash_flow,
        "cash": cash,
        "debt": debt,
    }


def calculate_dcf(
    current_fcf,
    growth_rate,
    discount_rate,
    terminal_growth_rate,
    forecast_years,
    cash,
    debt,
    shares_outstanding,
):
    projected_fcfs = []
    discounted_fcfs = []

    for year in range(1, forecast_years + 1):
        projected_fcf = current_fcf * (1 + growth_rate) ** year
        discounted_fcf = projected_fcf / (1 + discount_rate) ** year

        projected_fcfs.append(projected_fcf)
        discounted_fcfs.append(discounted_fcf)

    final_year_fcf = projected_fcfs[-1]

    terminal_value = (final_year_fcf * (1 + terminal_growth_rate)) / (
        discount_rate - terminal_growth_rate
    )

    present_value_terminal = terminal_value / (1 + discount_rate) ** forecast_years

    enterprise_value = sum(discounted_fcfs) + present_value_terminal
    equity_value = enterprise_value + cash - debt
    intrinsic_value_per_share = equity_value / shares_outstanding

    return {
        "projected_fcfs": projected_fcfs,
        "discounted_fcfs": discounted_fcfs,
        "terminal_value": terminal_value,
        "present_value_terminal": present_value_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_value_per_share": intrinsic_value_per_share,
    }


def dollars_billions(value):
    return f"${value / 1_000_000_000:,.2f}B"


def dollars(value):
    return f"${value:,.2f}"

# ------------------------------------------------------------
# Retrieve Data
# ------------------------------------------------------------

try:
    data = get_stock_data(ticker)
except Exception as error:
    st.error("Could not retrieve online stock data. Check the ticker symbol or internet connection.")
    st.stop()

company_name = data["company_name"]
current_price = data["current_price"]
auto_fcf = data["free_cash_flow"]
auto_shares = data["shares_outstanding"]
cash = data["cash"]
debt = data["debt"]

if use_manual_fcf:
    current_fcf = manual_fcf * 1_000_000_000
else:
    current_fcf = auto_fcf

if use_manual_shares:
    shares_outstanding = manual_shares * 1_000_000_000
else:
    shares_outstanding = auto_shares

# ------------------------------------------------------------
# Data Validation
# ------------------------------------------------------------

if current_price is None:
    st.error("Current market price could not be retrieved. Try another ticker or check your connection.")
    st.stop()

if current_fcf is None or current_fcf <= 0:
    st.error(
        "Free cash flow could not be retrieved or is negative. Turn on the manual free cash flow option in the sidebar."
    )
    st.stop()

if shares_outstanding is None or shares_outstanding <= 0:
    st.error(
        "Shares outstanding could not be retrieved. Turn on the manual shares outstanding option in the sidebar."
    )
    st.stop()

if discount_rate <= terminal_growth_rate:
    st.error("The discount rate must be greater than the terminal growth rate.")
    st.stop()

# ------------------------------------------------------------
# App Display
# ------------------------------------------------------------

st.header(f"Valuation for {company_name} ({ticker})")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Market Price", dollars(current_price))
col2.metric("Free Cash Flow Used", dollars_billions(current_fcf))
col3.metric("Cash", dollars_billions(cash))
col4.metric("Total Debt", dollars_billions(debt))

st.caption(
    "Market price, shares outstanding, cash, debt, and free cash flow are retrieved automatically through Yahoo Finance data using yfinance, unless manually overridden."
)

results = calculate_dcf(
    current_fcf=current_fcf,
    growth_rate=growth_rate,
    discount_rate=discount_rate,
    terminal_growth_rate=terminal_growth_rate,
    forecast_years=forecast_years,
    cash=cash,
    debt=debt,
    shares_outstanding=shares_outstanding,
)

intrinsic_value = results["intrinsic_value_per_share"]
upside_downside = ((intrinsic_value - current_price) / current_price) * 100

st.subheader("Final Valuation Result")

result_col1, result_col2, result_col3 = st.columns(3)
result_col1.metric("Estimated Intrinsic Value", dollars(intrinsic_value))
result_col2.metric("Current Market Price", dollars(current_price))
result_col3.metric("Upside / Downside", f"{upside_downside:,.2f}%")

if intrinsic_value > current_price:
    st.success("Conclusion: The stock appears undervalued based on these assumptions.")
elif intrinsic_value < current_price:
    st.error("Conclusion: The stock appears overvalued based on these assumptions.")
else:
    st.info("Conclusion: The stock appears fairly valued based on these assumptions.")

# ------------------------------------------------------------
# Step-by-Step Transparency
# ------------------------------------------------------------

st.header("Step-by-Step DCF Breakdown")

st.subheader("Step 1: Forecast Future Free Cash Flows")
st.write(
    "The model starts with current free cash flow and grows it each year by the selected growth rate."
)

fcf_table = pd.DataFrame({
    "Year": list(range(1, forecast_years + 1)),
    "Projected Free Cash Flow": results["projected_fcfs"],
    "Discounted Free Cash Flow": results["discounted_fcfs"],
})

fcf_table_display = fcf_table.copy()
fcf_table_display["Projected Free Cash Flow"] = fcf_table_display["Projected Free Cash Flow"].apply(dollars_billions)
fcf_table_display["Discounted Free Cash Flow"] = fcf_table_display["Discounted Free Cash Flow"].apply(dollars_billions)

st.table(fcf_table_display)

st.line_chart(
    fcf_table.set_index("Year")[["Projected Free Cash Flow", "Discounted Free Cash Flow"]]
)

st.subheader("Step 2: Calculate Terminal Value")
st.write(
    "Terminal value estimates the value of all cash flows after the explicit forecast period. "
    "This is important because most of a mature company's value often comes from cash flows beyond the first few forecast years."
)

st.metric("Terminal Value", dollars_billions(results["terminal_value"]))
st.metric("Present Value of Terminal Value", dollars_billions(results["present_value_terminal"]))

st.subheader("Step 3: Calculate Enterprise Value")
st.write(
    "Enterprise value equals the present value of forecast cash flows plus the present value of terminal value."
)
st.metric("Enterprise Value", dollars_billions(results["enterprise_value"]))

st.subheader("Step 4: Convert Enterprise Value to Equity Value")
st.write(
    "To move from enterprise value to equity value, the model adds cash and subtracts debt. "
    "This matters because shareholders own the equity value, not just the operating business value."
)

valuation_summary = pd.DataFrame({
    "Valuation Item": [
        "Enterprise Value",
        "Plus: Cash",
        "Less: Debt",
        "Equity Value",
        "Shares Outstanding",
        "Intrinsic Value Per Share",
    ],
    "Value": [
        dollars_billions(results["enterprise_value"]),
        dollars_billions(cash),
        dollars_billions(debt),
        dollars_billions(results["equity_value"]),
        f"{shares_outstanding / 1_000_000_000:,.2f}B shares",
        dollars(intrinsic_value),
    ],
})

st.table(valuation_summary)

# ------------------------------------------------------------
# Input Explanations
# ------------------------------------------------------------

st.header("Input Explanation Guide")

input_guide = pd.DataFrame({
    "Input": [
        "Ticker",
        "Free Cash Flow",
        "Growth Rate",
        "Discount Rate",
        "Terminal Growth Rate",
        "Forecast Period",
        "Cash",
        "Debt",
        "Shares Outstanding",
    ],
    "Meaning": [
        "The stock symbol of the company being valued. AAPL is Apple.",
        "Cash generated by the business after operating expenses and capital expenditures.",
        "Expected annual growth rate of future free cash flows.",
        "Required return used to discount future cash flows back to present value.",
        "Long-term growth rate after the forecast period.",
        "Number of years the model explicitly forecasts cash flows.",
        "Cash and equivalents held by the company.",
        "Total debt owed by the company.",
        "Number of shares used to calculate value per share.",
    ],
    "Why It Matters": [
        "The ticker determines which company data is retrieved.",
        "This is the foundation of the DCF model.",
        "Higher growth increases projected value.",
        "Higher discount rates decrease intrinsic value.",
        "This heavily affects terminal value, so it should be conservative.",
        "Longer forecasts allow more detail but also more uncertainty.",
        "Cash increases equity value.",
        "Debt reduces equity value.",
        "More shares lower the value per share."
    ]
})

st.dataframe(input_guide, use_container_width=True)

# ------------------------------------------------------------
# Formula Section
# ------------------------------------------------------------

st.header("DCF Formulas Used")

st.markdown(
    """
    **1. Projected Free Cash Flow**  
    Projected FCF = Current FCF × (1 + Growth Rate)^Year

    **2. Present Value of Free Cash Flow**  
    Present Value = Projected FCF / (1 + Discount Rate)^Year

    **3. Terminal Value**  
    Terminal Value = Final Year FCF × (1 + Terminal Growth Rate) / (Discount Rate - Terminal Growth Rate)

    **4. Enterprise Value**  
    Enterprise Value = Sum of Discounted FCFs + Present Value of Terminal Value

    **5. Equity Value**  
    Equity Value = Enterprise Value + Cash - Debt

    **6. Intrinsic Value Per Share**  
    Intrinsic Value Per Share = Equity Value / Shares Outstanding
    """
)

st.warning(
    "This valuation is not investment advice. It is an educational DCF model. "
    "The final answer depends heavily on assumptions, especially the growth rate, discount rate, and terminal growth rate."
)
st.header("Assumption Guidance")

st.info("""
For a mature company like Apple:
- FCF growth rate is usually modeled conservatively, often around 2%–8%.
- Discount rate is commonly around 8%–12%, depending on risk.
- Terminal growth rate should usually stay around 2%–3%, because it should not exceed long-term economic growth.
""")