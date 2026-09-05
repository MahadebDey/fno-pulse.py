import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# ================= 1. Page Configuration & Custom CSS =================
st.set_page_config(
    page_title="Mahadeb Stock Research",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Mobile-Friendly Styling
st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    .metric-card {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #2A2E39 !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Mahadeb Stock Research")
st.caption("Institutional Intelligence: Technical Radar (VWAP, PDH/PDL, 52W), Results, TV Picks & Brokerage Targets")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 2. F&O Universe & Sector Mapping =================
STOCK_SECTOR_MAP = {
    # Banking & Financials
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "BANKBARODA": "Banking", "PNB": "Banking",
    "BAJFINANCE": "Financials", "BAJAJFINSV": "Financials", "CHOLAFIN": "Financials", "MUTHOOTFIN": "Financials",
    "PFC": "Financials", "RECLTD": "Financials", "SHRIRAMFIN": "Financials", "MOTILALOFS": "Financials",
    
    # IT & Tech
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT", 
    "LTIM": "IT", "COFORGE": "IT", "PERSISTENT": "IT", "MPHASIS": "IT", "NAUKRI": "IT",
    
    # Auto & Ancillaries
    "TATAMOTORS": "Auto", "MARUTI": "Auto", "M&M": "Auto", "BAJAJ-AUTO": "Auto", 
    "HEROMOTOCO": "Auto", "EICHERMOT": "Auto", "TVSMOTOR": "Auto", "BHARATFORG": "Auto", 
    "APOLLOTYRE": "Auto", "BALKRISIND": "Auto", "MOTHERSON": "Auto",
    
    # Metals & Mining
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals", "JINDALSTEL": "Metals", 
    "VEDL": "Metals", "COALINDIA": "Metals", "NMDC": "Metals", "NATIONALUM": "Metals", "SAIL": "Metals",
    
    # Energy, Oil & Power
    "RELIANCE": "Energy/Oil", "BPCL": "Energy/Oil", "IOC": "Energy/Oil", "ONGC": "Energy/Oil", 
    "NTPC": "Power", "POWERGRID": "Power", "TATAPOWER": "Power", "ADANIENT": "Energy", "ADANIPORTS": "Infra",
    
    # Pharma & Healthcare
    "SUNPHARMA": "Pharma", "CIPLA": "Pharma", "DRREDDY": "Pharma", "DIVISLAB": "Pharma", 
    "LUPIN": "Pharma", "AUROPHARMA": "Pharma", "APOLLOHOSP": "Pharma", "ZYDUSLIFE": "Pharma",
    
    # FMCG & Consumption
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG", 
    "DABUR": "FMCG", "TATACONSUM": "FMCG", "TITAN": "Consumer", "ASIANPAINT": "Consumer",
    
    # Infra & Cables
    "LT": "Infra", "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement", 
    "POLYCAB": "Cables", "HAVELLS": "Consumer Elec", "DIXON": "Electronics", "DLF": "Realty"
}

ALL_FNO_STOCKS = sorted(list(STOCK_SECTOR_MAP.keys()))

# ================= 3. Technical Analytics Engine (VWAP + Breakouts) =================
def compute_stock_technicals(symbol):
    ticker = f"{symbol}.NS"
    try:
        # Daily candle data for PDH, PDL, 52W High/Low and 20 EMA
        daily = yf.download(ticker, period="1y", interval="1d", progress=False)
        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.get_level_values(0)
            
        if len(daily) < 30:
            return None

        cmp_val = round(float(daily['Close'].iloc[-1]), 2)
        pdh = round(float(daily['High'].iloc[-2]), 2)
        pdl = round(float(daily['Low'].iloc[-2]), 2)
        high_52w = round(float(daily['High'].max()), 2)
        low_52w = round(float(daily['Low'].min()), 2)
        ema20 = round(float(daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)

        # 5-minute candle data for VWAP calculation
        intra = yf.download(ticker, period="1d", interval="5m", progress=False)
        if isinstance(intra.columns, pd.MultiIndex):
            intra.columns = intra.columns.get_level_values(0)

        if not intra.empty and 'Volume' in intra and intra['Volume'].sum() > 0:
            typical_price = (intra['High'] + intra['Low'] + intra['Close']) / 3
            vwap_val = round(float((typical_price * intra['Volume']).sum() / intra['Volume'].sum()), 2)
            vwap_alert = "🟢 Above VWAP" if cmp_val >= vwap_val else "🔴 Below VWAP"
        else:
            vwap_val = cmp_val
            vwap_alert = "⚪ At VWAP"

        # PDH / PDL Breakout check
        if cmp_val > pdh:
            pd_alert = "🟢 PDH Breakout"
        elif cmp_val < pdl:
            pd_alert = "🔴 PDL Breakdown"
        else:
            pd_alert = "⚪ Inside Range"

        # 52-Week Range Proximity (within 2.5%)
        pct_52h = ((high_52w - cmp_val) / high_52w) * 100
        pct_52l = ((cmp_val - low_52w) / low_52w) * 100
        if pct_52h <= 2.5:
            high_low_flag = f"🚀 Near 52W High ({high_52w})"
        elif pct_52l <= 2.5:
            high_low_flag = f"⚠️ Near 52W Low ({low_52w})"
        else:
            high_low_flag = "Normal Range"

        # Trend bias relative to 20 EMA
        trend_status = "🟢 Bullish (> 20 EMA)" if cmp_val >= ema20 else "🔴 Bearish (< 20 EMA)"

        return {
            "Stock": symbol,
            "Sector": STOCK_SECTOR_MAP.get(symbol, "General"),
            "CMP (₹)": cmp_val,
            "VWAP (₹)": vwap_val,
            "VWAP Alert": vwap_alert,
            "PDH/PDL": pd_alert,
            "52W Status": high_low_flag,
            "20 EMA Trend": trend_status,
            "PDH (₹)": pdh,
            "PDL (₹)": pdl
        }
    except Exception:
        return None

# ================= 4. News & Sentiment Parsers =================
def analyze_earnings_verdict(text):
    t = text.lower()
    bull_keys = ["profit jumps", "pat rises", "net profit up", "beats estimates", "beat estimates", "revenue up", "margin expands", "profit surges"]
    bear_keys = ["profit falls", "pat drops", "net loss", "misses estimates", "miss estimates", "margin drops", "revenue declines"]
    if any(k in t for k in bull_keys): return "🟢 BULLISH RESULT", "Beat Estimates / Profit Surge"
    if any(k in t for k in bear_keys): return "🔴 BEARISH RESULT", "Missed Estimates / Margin Drag"
    return "⚪ IN-LINE / GENERAL", "Financial Announcement"

def analyze_news_impact(text):
    t = text.lower()
    pos_keys = ["bags order", "wins contract", "approval", "acquires", "upgrade", "joint venture", "expansion", "target raised"]
    neg_keys = ["penalty", "probe", "raid", "sebi notice", "usfda oai", "warning letter", "fire", "resigns", "downgrade"]
    if any(k in t for k in pos_keys): return "🟢 POSITIVE IMPACT"
    if any(k in t for k in neg_keys): return "🔴 NEGATIVE IMPACT"
    return "⚪ GENERAL HEADLINE"

def fetch_rss_feed(query, limit=12):
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:limit]:
                title = entry.find("title").text
                link = entry.find("link").text
                date = entry.find("pubDate").text
                
                matched = "MARKET"
                for stk in ALL_FNO_STOCKS:
                    if stk.lower() in title.lower():
                        matched = stk
                        break
                results.append({"stock": matched, "title": title, "link": link, "date": date})
    except Exception:
        pass
    return results

# ================= 5. TOP-TO-BOTTOM SERIAL INTERFACE =================

# SECTION 1: Technical & Intraday VWAP Radar
with st.expander("🎯 SECTION 1: Technical & Intraday VWAP Radar", expanded=True):
    st.write("**Scan stocks across VWAP, PDH/PDL breakouts, 52-Week highs/lows, and 20-EMA trends.**")
    scan_vol = st.slider("Select F&O universe volume for analysis:", min_value=10, max_value=len(ALL_FNO_STOCKS), value=20, step=5)
    
    if st.button("🚀 Run Real-Time Technical Scanner", use_container_width=True, key="btn_run_tech"):
        with st.spinner(f"Computing VWAP & Breakouts for top {scan_vol} stocks..."):
            stock_sublist = ALL_FNO_STOCKS[:scan_vol]
            data_pile = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                scanned_items = executor.map(compute_stock_technicals, stock_sublist)
                for item in scanned_items:
                    if item:
                        data_pile.append(item)

            if data_pile:
                tdf = pd.DataFrame(data_pile)
                
                # Highlight Metrics
                above_vwap = tdf[tdf['VWAP Alert'] == "🟢 Above VWAP"]
                pdh_break = tdf[tdf['PDH/PDL'] == "🟢 PDH Breakout"]
                pdl_break = tdf[tdf['PDH/PDL'] == "🔴 PDL Breakdown"]

                c1, c2, c3 = st.columns(3)
                c1.metric("Above VWAP", f"{len(above_vwap)} / {len(tdf)}")
                c2.metric("PDH Breakouts", len(pdh_break))
                c3.metric("PDL Breakdowns", len(pdl_break))

                st.write("---")
                st.dataframe(
                    tdf[["Stock", "Sector", "CMP (₹)", "VWAP (₹)", "VWAP Alert", "PDH/PDL", "52W Status", "20 EMA Trend"]], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.warning("Could not fetch candle data. Please try again.")

# SECTION 2: Earnings Verdicts
with st.expander("📊 SECTION 2: Corporate Results & Earnings Verdicts", expanded=False):
    st.write("**Automated earnings intelligence assessing quarterly results against market benchmarks.**")
    if st.button("🔄 Fetch Latest Quarterly Results", use_container_width=True, key="btn_res"):
        with st.spinner("Analyzing corporate result filings..."):
            res_list = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=15)
            if res_list:
                for r in res_list:
                    verdict, desc = analyze_earnings_verdict(r['title'])
                    st.markdown(f"**[{verdict}]** `{r['stock']}` — *{desc}*")
                    st.markdown(f"[{r['title']}]({r['link']})")
                    st.caption(f"Filed: {r['date']}")
                    st.divider()
            else:
                st.info("No earnings announcements detected.")

# SECTION 3: High-Impact News
with st.expander("⚡ SECTION 3: High-Impact Breaking News", expanded=False):
    st.write("**Material corporate developments: SEBI actions, major orders, acquisitions, and regulatory audits.**")
    if st.button("🔄 Pull High-Impact Market Movers", use_container_width=True, key="btn_impact"):
        with st.spinner("Scanning material headlines..."):
            news_list = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda+OR+acquisition)+share+India", limit=15)
            if news_list:
                for n in news_list:
                    tag = analyze_news_impact(n['title'])
                    st.markdown(f"**[{tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.caption(f"Time: {n['date']}")
                    st.divider()
            else:
                st.info("No material corporate alerts found.")

# SECTION 4: Business TV Research
with st.expander("📺 SECTION 4: Zee Business & CNBC Awaaz Research", expanded=False):
    st.write("**TV panelist recommendations, trading ideas, and stock calls from leading business channels.**")
    if st.button("🔄 Scan TV Research Feeds", use_container_width=True, key="btn_tv"):
        with st.spinner("Parsing television research alerts..."):
            tv_list = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=15)
            if tv_list:
                for t in tv_list:
                    src = "🟢 Zee Business" if "zee" in t['title'].lower() else ("🔵 CNBC Awaaz" if "cnbc" in t['title'].lower() else "📺 Business TV")
                    st.markdown(f"**[{src}]** `{t['stock']}` | [{t['title']}]({t['link']})")
                    st.caption(f"Broadcast Time: {t['date']}")
                    st.divider()
            else:
                st.info("No recent TV calls detected.")

# SECTION 5: Institutional Brokerage Targets
with st.expander("🎯 SECTION 5: Brokerage Ratings & Target Upgrades", expanded=False):
    st.write("**Target revisions and ratings from Morgan Stanley, Jefferies, CLSA, and domestic brokerages.**")
    if st.button("🔄 Pull Brokerage Target Changes", use_container_width=True, key="btn_brok"):
        with st.spinner("Retrieving broker reports..."):
            brok_list = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=15)
            if brok_list:
                for b in brok_list:
                    t_low = b['title'].lower()
                    call = "🟢 BUY / TARGET UP" if any(w in t_low for w in ["buy", "raised", "upgrade"]) else ("🔴 SELL / TARGET CUT" if any(w in t_low for w in ["sell", "cut", "downgrade"]) else "⚪ TARGET REVISED")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.caption(f"Release: {b['date']}")
                    st.divider()
            else:
                st.info("No recent brokerage updates identified.")

# SECTION 6: Single Stock Dedicated Lookup
with st.expander("🔍 SECTION 6: Single Stock Deep-Dive", expanded=False):
    target_symbol = st.selectbox("Select any F&O stock for complete intel:", ALL_FNO_STOCKS)
    if st.button(f"Generate Deep-Dive for {target_symbol}", use_container_width=True):
        with st.spinner(f"Compiling complete file for {target_symbol}..."):
            # Compute technicals
            tech_info = compute_stock_technicals(target_symbol)
            if tech_info:
                st.write("#### 📈 Technical Pulse")
                m1, m2, m3 = st.columns(3)
                m1.metric("CMP", f"₹{tech_info['CMP (₹)']}")
                m2.metric("VWAP", f"₹{tech_info['VWAP (₹)']}", delta=tech_info['VWAP Alert'])
                m3.metric("PDH / PDL", tech_info['PDH/PDL'])
                st.caption(f"Sector: {tech_info['Sector']} | 52W Proximity: {tech_info['52W Status']} | Trend: {tech_info['20 EMA Trend']}")
            
            st.write("#### 📰 Recent Headlines & Research")
            custom_feed = fetch_rss_feed(f"{target_symbol}+share+India", limit=5)
            if custom_feed:
                for item in custom_feed:
                    st.markdown(f"• [{item['title']}]({item['link']})")
                    st.caption(f"Time: {item['date']}")
            else:
                st.info("No direct news items detected.")
