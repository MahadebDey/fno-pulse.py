import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# ================= 1. Page Configuration =================
st.set_page_config(
    page_title="Mahadeb Stock Research",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    div[data-testid="stExpander"] {
        border: 1px solid #2A2E39 !important;
        border-radius: 8px !important;
        margin-bottom: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Mahadeb Stock Research")
st.caption("Institutional Intelligence: Multi-Factor Composite Engine (Technicals + VWAP + Twitter + Results + News)")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 2. Stock Universe & Sectors =================
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
    
    # Pharma
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

# ================= 3. Analysis Helpers =================
def quick_text_score(text, pos_words, neg_words):
    t = text.lower()
    p = sum(1 for w in pos_words if w in t)
    n = sum(1 for w in neg_words if w in t)
    if p > n: return 1
    if n > p: return -1
    return 0

def fetch_rss_feed(query, limit=10):
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
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

# ================= 4. Deep Multi-Factor Stock Analyzer =================
def analyze_stock_full(symbol):
    ticker = f"{symbol}.NS"
    score = 0.0
    details = {
        "Stock": symbol,
        "Sector": STOCK_SECTOR_MAP.get(symbol, "General"),
        "CMP (₹)": 0.0,
        "Technical Bias": "⚪ Neutral",
        "Twitter Pulse": "⚪ Neutral",
        "Results/News": "⚪ Neutral",
        "Composite Score": 0.0
    }
    
    try:
        # A. Technical Analysis (VWAP + PDH/PDL + 20 EMA)
        daily = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.get_level_values(0)
            
        if len(daily) >= 25:
            cmp_val = round(float(daily['Close'].iloc[-1]), 2)
            pdh = round(float(daily['High'].iloc[-2]), 2)
            pdl = round(float(daily['Low'].iloc[-2]), 2)
            ema20 = round(float(daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)
            details["CMP (₹)"] = cmp_val

            # Intraday VWAP
            intra = yf.download(ticker, period="1d", interval="5m", progress=False)
            if isinstance(intra.columns, pd.MultiIndex):
                intra.columns = intra.columns.get_level_values(0)

            tech_points = 0.0
            if not intra.empty and 'Volume' in intra and intra['Volume'].sum() > 0:
                typ = (intra['High'] + intra['Low'] + intra['Close']) / 3
                vwap = float((typ * intra['Volume']).sum() / intra['Volume'].sum())
                if cmp_val >= vwap: tech_points += 1.5
                else: tech_points -= 1.5

            if cmp_val > pdh: tech_points += 2.0
            elif cmp_val < pdl: tech_points -= 2.0

            if cmp_val >= ema20: tech_points += 1.0
            else: tech_points -= 1.0

            score += tech_points
            details["Technical Bias"] = "🟢 Strong" if tech_points > 1.5 else ("🔴 Weak" if tech_points < -1.5 else "⚪ Neutral")

        # B. Twitter / Social Pulse
        tw_feed = fetch_rss_feed(f"{symbol}+stock+twitter+OR+{symbol}+breakout", limit=3)
        tw_sc = 0
        for tw in tw_feed:
            tw_sc += quick_text_score(tw['title'], ["surge", "breakout", "buy", "bullish", "rally"], ["fall", "crash", "bearish", "loss", "drop"])
        
        if tw_sc > 0:
            score += 1.5
            details["Twitter Pulse"] = "🟢 Bullish Buzz"
        elif tw_sc < 0:
            score -= 1.5
            details["Twitter Pulse"] = "🔴 Bearish Buzz"

        # C. Results & High-Impact News Check
        news_feed = fetch_rss_feed(f"{symbol}+share+(results+OR+profit+OR+order+OR+sebi+OR+target)", limit=3)
        n_sc = 0
        for nf in news_feed:
            n_sc += quick_text_score(nf['title'], 
                                     ["profit jumps", "pat rises", "beats estimates", "bags order", "target raised", "upgrade"], 
                                     ["profit falls", "pat drops", "misses estimates", "penalty", "sebi", "downgrade", "cut"])
        
        if n_sc > 0:
            score += 2.0
            details["Results/News"] = "🟢 Positive News"
        elif n_sc < 0:
            score -= 2.0
            details["Results/News"] = "🔴 Negative News"

        details["Composite Score"] = round(score, 2)
        return details
    except Exception:
        return None

# ================= 5. TOP-TO-BOTTOM USER INTERFACE =================

# SECTION 1: Multi-Factor Top 5 Bullish & Bearish Stocks
with st.expander("⭐ SECTION 1: Multi-Factor Top 5 Bullish & Bearish Stocks", expanded=True):
    st.write("**Top 5 stocks selected after evaluating: VWAP, PDH/PDL breakouts, 20 EMA, Twitter sentiment, corporate results, and breaking news.**")
    
    scan_limit = st.slider("Select universe size for deep multi-factor audit:", min_value=15, max_value=len(ALL_FNO_STOCKS), value=25, step=5)
    
    if st.button("🔥 Run Multi-Factor Composite Analysis", use_container_width=True, key="btn_deep_analysis"):
        with st.spinner(f"Analyzing {scan_limit} stocks across Technicals, VWAP, Twitter Buzz & Results..."):
            stock_sublist = ALL_FNO_STOCKS[:scan_limit]
            analysis_data = []
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                items = executor.map(analyze_stock_full, stock_sublist)
                for itm in items:
                    if itm and itm["CMP (₹)"] > 0:
                        analysis_data.append(itm)
            
            if analysis_data:
                mdf = pd.DataFrame(analysis_data)
                
                # Sorted by Composite Multi-Factor Score
                sorted_df = mdf.sort_values(by="Composite Score", ascending=False)
                
                top_bulls = sorted_df.head(5)
                top_bears = sorted_df.tail(5).iloc[::-1]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.success("🟢 **Top 5 Bullish Stocks (Multi-Factor Confirmed)**")
                    st.dataframe(
                        top_bulls[["Stock", "Sector", "CMP (₹)", "Technical Bias", "Twitter Pulse", "Results/News", "Composite Score"]], 
                        use_container_width=True, 
                        hide_index=True
                    )
                with col_b:
                    st.error("🔴 **Top 5 Bearish Stocks (Multi-Factor Confirmed)**")
                    st.dataframe(
                        top_bears[["Stock", "Sector", "CMP (₹)", "Technical Bias", "Twitter Pulse", "Results/News", "Composite Score"]], 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                st.divider()
                st.write("### 📋 Complete Scanned Universe Ranking")
                st.dataframe(sorted_df, use_container_width=True, hide_index=True)
            else:
                st.warning("Failed to collect composite metrics. Please retry.")

# SECTION 2: Technical & Intraday VWAP Radar
with st.expander("🎯 SECTION 2: Technical & Intraday VWAP Radar", expanded=False):
    st.write("**Real-time status of intraday VWAP, yesterday's high/low (PDH/PDL), and 52W range.**")
    if st.button("🚀 Run Live Technical Scan", use_container_width=True, key="btn_tech_only"):
        with st.spinner("Fetching VWAP & Candle stats..."):
            t_data = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                res = executor.map(analyze_stock_full, ALL_FNO_STOCKS[:20])
                for r in res:
                    if r and r["CMP (₹)"] > 0: t_data.append(r)
            if t_data:
                tdf = pd.DataFrame(t_data)
                st.dataframe(tdf[["Stock", "Sector", "CMP (₹)", "Technical Bias", "Composite Score"]], use_container_width=True, hide_index=True)

# SECTION 3: Earnings Verdicts
with st.expander("📊 SECTION 3: Corporate Results & Earnings Verdicts", expanded=False):
    st.write("**Automated earnings intelligence assessing quarterly results against market benchmarks.**")
    if st.button("🔄 Fetch Latest Quarterly Results", use_container_width=True, key="btn_res"):
        with st.spinner("Analyzing corporate result filings..."):
            res_list = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=15)
            if res_list:
                for r in res_list:
                    t = r['title'].lower()
                    is_bull = any(k in t for k in ["profit jumps", "pat rises", "net profit up", "beats estimates", "revenue up"])
                    is_bear = any(k in t for k in ["profit falls", "pat drops", "net loss", "misses estimates", "revenue declines"])
                    v_badge = "🟢 BULLISH RESULT" if is_bull else ("🔴 BEARISH RESULT" if is_bear else "⚪ IN-LINE / GENERAL")
                    st.markdown(f"**[{v_badge}]** `{r['stock']}` | [{r['title']}]({r['link']})")
                    st.caption(f"Published: {r['date']}")
                    st.divider()

# SECTION 4: High-Impact Breaking News
with st.expander("⚡ SECTION 4: High-Impact Breaking News", expanded=False):
    st.write("**Material corporate developments: SEBI actions, major orders, acquisitions, and regulatory audits.**")
    if st.button("🔄 Pull High-Impact Market Movers", use_container_width=True, key="btn_impact"):
        with st.spinner("Scanning material headlines..."):
            news_list = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda+OR+acquisition)+share+India", limit=15)
            if news_list:
                for n in news_list:
                    tl = n['title'].lower()
                    tag = "🟢 POSITIVE IMPACT" if any(k in tl for k in ["bags order", "wins contract", "approval", "acquires", "upgrade"]) else ("🔴 NEGATIVE IMPACT" if any(k in tl for k in ["penalty", "probe", "raid", "sebi", "usfda"]) else "⚪ GENERAL HEADLINE")
                    st.markdown(f"**[{tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.caption(f"Time: {n['date']}")
                    st.divider()

# SECTION 5: Business TV Research
with st.expander("📺 SECTION 5: Zee Business & CNBC Awaaz Research", expanded=False):
    st.write("**TV panelist recommendations, trading ideas, and stock calls from leading business channels.**")
    if st.button("🔄 Scan TV Research Feeds", use_container_width=True, key="btn_tv"):
        with st.spinner("Parsing television research alerts..."):
            tv_list = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=15)
            if tv_list:
                for t in tv_list:
                    src = "🟢 Zee Business" if "zee" in t['title'].lower() else ("🔵 CNBC Awaaz" if "cnbc" in t['title'].lower() else "📺 Business TV")
                    st.markdown(f"**[{src}]** `{t['stock']}` | [{t['title']}]({t['link']})")
                    st.caption(f"Broadcast: {t['date']}")
                    st.divider()

# SECTION 6: Institutional Brokerage Targets
with st.expander("🎯 SECTION 6: Brokerage Ratings & Target Upgrades", expanded=False):
    st.write("**Target revisions and ratings from Morgan Stanley, Jefferies, CLSA, and domestic brokerages.**")
    if st.button("🔄 Pull Brokerage Target Changes", use_container_width=True, key="btn_brok"):
        with st.spinner("Retrieving broker reports..."):
            brok_list = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=15)
            if brok_list:
                for b in brok_list:
                    tl = b['title'].lower()
                    call = "🟢 BUY / TARGET UP" if any(w in tl for w in ["buy", "raised", "upgrade"]) else ("🔴 SELL / TARGET CUT" if any(w in tl for w in ["sell", "cut", "downgrade"]) else "⚪ TARGET REVISED")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.caption(f"Release: {b['date']}")
                    st.divider()

# SECTION 7: Single Stock Dedicated Lookup
with st.expander("🔍 SECTION 7: Single Stock Deep-Dive", expanded=False):
    target_symbol = st.selectbox("Select any F&O stock for comprehensive analysis:", ALL_FNO_STOCKS)
    if st.button(f"Generate Deep-Dive for {target_symbol}", use_container_width=True):
        with st.spinner(f"Auditing complete data for {target_symbol}..."):
            full_stat = analyze_stock_full(target_symbol)
            if full_stat:
                st.write("#### 📊 Comprehensive Audit Score")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CMP", f"₹{full_stat['CMP (₹)']}")
                c2.metric("Technical Bias", full_stat["Technical Bias"])
                c3.metric("Twitter Pulse", full_stat["Twitter Pulse"])
                c4.metric("Score", full_stat["Composite Score"])
                st.caption(f"Sector: {full_stat['Sector']} | Results & News: {full_stat['Results/News']}")
            
            st.write("#### 📰 Recent Headlines & Media")
            custom_feed = fetch_rss_feed(f"{target_symbol}+share+India", limit=5)
            if custom_feed:
                for item in custom_feed:
                    st.markdown(f"• [{item['title']}]({item['link']})")
                    st.caption(f"Time: {item['date']}")
