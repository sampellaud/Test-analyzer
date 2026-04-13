import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import requests

st.set_page_config(page_title="Portfolio Analyzer", page_icon="📊", layout="wide")

st.title("📊 Portfolio Analyzer")

st.markdown("Search for a stock by ticker, company name, ISIN or valor — we fetch everything else automatically.")

# ── Region mapping by exchange ────────────────────────────────────────────────
def get_region(ticker_info):
    exchange = ticker_info.get("exchange", "")
    country  = ticker_info.get("country", "")
    mapping = {
        "NMS": "North America", "NYQ": "North America", "NGM": "North America",
        "PCX": "North America", "ASE": "North America", "TSX": "North America",
        "LSE": "Europe", "XETRA": "Europe", "EPA": "Europe", "BIT": "Europe",
        "SWX": "Europe", "AMS": "Europe", "MCE": "Europe",
        "TYO": "Asia", "HKG": "Asia", "SHH": "Asia", "SHZ": "Asia",
        "NSE": "Asia", "BSE": "Asia", "KSC": "Asia", "TWO": "Asia",
        "ASX": "Oceania",
        "SAO": "Latin America", "BMV": "Latin America",
        "TLV": "Middle East", "DFM": "Middle East",
        "JSE": "Africa",
    }
    return mapping.get(exchange, country if country else "Other")

# ── Risk based on beta ────────────────────────────────────────────────────────
def get_risk(beta):
    if beta is None:
        return "Unknown"
    if beta < 0.8:
        return "Low"
    elif beta < 1.3:
        return "Medium"
    else:
        return "High"

# ── Search Yahoo Finance ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def search_stocks(query):
    if not query or len(query) < 2:
        return []
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=8&newsCount=0&enableFuzzyQuery=true"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        results = []
        for item in data.get("quotes", []):
            ticker   = item.get("symbol", "")
            name     = item.get("longname") or item.get("shortname") or ""
            exchange = item.get("exchDisp", "")
            typ      = item.get("quoteType", "")
            if ticker and typ in ("EQUITY", "ETF", "MUTUALFUND"):
                label = f"{ticker} — {name} ({exchange})"
                results.append({"label": label, "ticker": ticker, "name": name})
        return results
    except Exception:
        return []

# ── Fetch stock data from Yahoo Finance ──────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_stock(ticker, quantity):
    try:
        t    = yf.Ticker(ticker)
        info = t.info
        price    = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        currency = info.get("currency", "USD")
        industry = info.get("industry") or info.get("sector") or "Unknown"
        beta     = info.get("beta")
        name     = info.get("shortName") or ticker

        if price is None:
            return None, f"Could not get price for **{ticker}**"

        value  = round(price * quantity, 2)
        region = get_region(info)
        risk   = get_risk(beta)

        return {
            "Ticker":      ticker.upper(),
            "Name":        name,
            "Quantity":    quantity,
            "Price":       price,
            "Currency":    currency,
            "Value (USD)": value,
            "Industry":    industry,
            "Region":      region,
            "Risk":        risk,
        }, None
    except Exception as e:
        return None, f"Error fetching **{ticker}**: {str(e)}"

# ── Session state ─────────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []

# ── Search section ────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🔍 Search & add stocks")
st.caption("Start typing a ticker (AAPL), company name (Apple), ISIN or valor number")

search_query = st.text_input("Search for a stock",
                              placeholder="e.g. Apple, AAPL, NESN, CH0012221716...",
                              key="search_box")

selected_ticker = None
selected_name   = None

if search_query:
    with st.spinner("Searching..."):
        results = search_stocks(search_query)

    if results:
        options = ["— select a stock —"] + [r["label"] for r in results]
        chosen  = st.selectbox("Matching stocks:", options, key="search_select")

        if chosen != "— select a stock —":
            match = next((r for r in results if r["label"] == chosen), None)
            if match:
                selected_ticker = match["ticker"]
                selected_name   = match["name"]
    else:
        st.warning("No results found. Try a different search term.")

if selected_ticker:
    col_qty, col_btn = st.columns([2, 1])
    with col_qty:
        qty = st.number_input(f"Quantity for {selected_ticker}",
                              min_value=1, value=1, key="qty_input")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add to portfolio", type="primary"):
            already = any(r["ticker"] == selected_ticker for r in st.session_state.portfolio)
            if already:
                st.warning(f"{selected_ticker} is already in your portfolio!")
            else:
                st.session_state.portfolio.append({
                    "ticker":   selected_ticker,
                    "name":     selected_name,
                    "quantity": qty,
                })
                st.success(f"✅ Added {selected_ticker}!")
                st.rerun()

# ── Current portfolio list ────────────────────────────────────────────────────
st.markdown("---")

col_sample, col_clear = st.columns([2, 5])
with col_sample:
    if st.button("🔄 Load sample portfolio"):
        st.session_state.portfolio = [
            {"ticker": "AAPL",    "name": "Apple Inc.",   "quantity": 10},
            {"ticker": "NESN.SW", "name": "Nestlé S.A.",  "quantity": 5},
            {"ticker": "TSLA",    "name": "Tesla Inc.",    "quantity": 3},
            {"ticker": "BABA",    "name": "Alibaba Group", "quantity": 8},
            {"ticker": "LVMUY",   "name": "LVMH",          "quantity": 4},
        ]
        st.rerun()
with col_clear:
    if st.button("🗑️ Clear all") and st.session_state.portfolio:
        st.session_state.portfolio = []
        st.rerun()

if st.session_state.portfolio:
    st.subheader("Your portfolio")
    updated_rows = []
    for i, row in enumerate(st.session_state.portfolio):
        c1, c2, c3, c4 = st.columns([1.5, 3, 1.5, 0.5])
        c1.markdown(f"**{row['ticker']}**")
        c2.markdown(row.get("name", ""))
        quantity = c3.number_input("Qty", value=int(row["quantity"]),
                                   min_value=1, key=f"qty_{i}",
                                   label_visibility="collapsed")
        remove = c4.button("❌", key=f"del_{i}")
        if not remove:
            updated_rows.append({**row, "quantity": quantity})
    st.session_state.portfolio = updated_rows
else:
    st.info("👆 Search for a stock above to build your portfolio.")

# ── Analyze button ────────────────────────────────────────────────────────────
st.markdown("")
analyze = st.button("🔍 Analyze Portfolio", type="primary", use_container_width=True)

if analyze:
    rows = st.session_state.portfolio
    if not rows:
        st.warning("Please add at least one stock first.")
    else:
        results = []
        errors  = []
        with st.spinner("Fetching data from Yahoo Finance..."):
            for row in rows:
                data, err = fetch_stock(row["ticker"], row["quantity"])
                if data:
                    results.append(data)
                else:
                    errors.append(err)

        for e in errors:
            st.error(e)

        if results:
            df    = pd.DataFrame(results)
            total = df["Value (USD)"].sum()

            st.markdown("---")
            st.subheader("📈 Portfolio Breakdown")
            st.metric("Total Portfolio Value", f"${total:,.2f}")

            COLORS = px.colors.qualitative.Set3

            def make_pie(group_col, title):
                grouped = df.groupby(group_col)["Value (USD)"].sum().reset_index()
                grouped.columns = [group_col, "Value"]
                fig = px.pie(grouped, values="Value", names=group_col,
                             title=title, color_discrete_sequence=COLORS, hole=0.35)
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(showlegend=True, title_font_size=16,
                                  margin=dict(t=60, b=20, l=20, r=20))
                return fig

            def make_risk_pie(title):
                risk_groups = df.groupby("Risk").apply(
                    lambda g: "<br>".join(
                        f"{row['Ticker']} ({row['Name']}): ${row['Value (USD)']:,.0f}"
                        for _, row in g.iterrows()
                    )
                ).reset_index()
                risk_groups.columns = ["Risk", "Stocks"]
                grouped = df.groupby("Risk")["Value (USD)"].sum().reset_index()
                grouped.columns = ["Risk", "Value"]
                grouped = grouped.merge(risk_groups, on="Risk")
                fig = px.pie(grouped, values="Value", names="Risk",
                             title=title, color_discrete_sequence=COLORS,
                             hole=0.35, custom_data=["Stocks"])
                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>Value: $%{value:,.0f}<br>(%{percent})<br><br>Stocks:<br>%{customdata[0]}<extra></extra>"
                )
                fig.update_layout(showlegend=True, title_font_size=16,
                                  margin=dict(t=60, b=20, l=20, r=20))
                return fig

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(make_pie("Currency", "By Currency"), use_container_width=True)
                st.plotly_chart(make_pie("Region",   "By Region"),   use_container_width=True)
            with col2:
                st.plotly_chart(make_pie("Industry", "By Industry"), use_container_width=True)
                st.plotly_chart(make_risk_pie("By Risk"), use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Portfolio Summary")
            df["Weight (%)"] = (df["Value (USD)"] / total * 100).round(2)
            st.dataframe(
                df[["Ticker", "Name", "Quantity", "Price", "Currency",
                    "Value (USD)", "Weight (%)", "Industry", "Region", "Risk"]]
                .sort_values("Value (USD)", ascending=False),
                use_container_width=True
            )
