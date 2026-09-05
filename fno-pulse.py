import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# ================= Page Configuration =================
st.set_page_config(
    page_title="Mahadeb Stock Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📈 Mahadeb Stock Research")
st.caption("Automated F&O Market Scanner: Earnings Verdicts, High-Impact News, TV Research & Brokerage Targets")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 1. F&O Stocks & Sector Mapping =================
STOCK_SECTOR_MAP = {
    # Banking & Financial Services
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
    
    # Infrastructure, Cement & Cables
    "LT": "Infra", "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement", 
    "POLYCAB": "Cables", "HAVELLS": "Consumer Elec", "DIXON": "Electronics", "DLF": "Realty"
}

ALL_FNO_STOCKS = sorted(list(STOCK_SECTOR_MAP.keys()))

# ================= 2. Intelligence & Sentiment Engines =================
def analyze_earnings_verdict(text):
    t = text.lower()
    bull_keys = [
        "profit jumps", "pat rises", "net profit up", "beats estimates", "beat estimates", 
        "revenue up", "margin expands", "dividend declared", "strong q", "robust growth", 
        "ebitda jumps", "guidance raised", "profit surges", "quarterly net rises"
    ]
    bear_keys = [
        "profit falls", "pat drops", "net loss", "misses estimates", "miss estimates", 
        "margin drops", "ebitda falls", "slumps", "plunges", "weak q", "guidance cut", 
        "revenue declines", "net profit drops"
    ]
    
    is_bull = any(k in t for k in bull_keys)
    is_bear = any(k in t for k in bear_keys)
    
    if is_bull and not is_bear:
        return "🟢 BULLISH RESULT", "Beat Estimates / Strong Profit Growth"
    elif is_bear and not is_bull:
        return "🔴 BEARISH RESULT", "Missed Estimates / Margin Compression / Loss"
    return "⚪ IN-LINE / NEUTRAL", "Earnings Announcement / Inline Performance"

def analyze_news_impact(text):
    t = text.lower()
    pos_keys = [
        "bags order", "wins contract", "approval", "acquires", "upgrade", "joint venture", 
        "expansion", "commissioned", "target raised", "surges", "green signal", "secures"
    ]
    neg_keys = [
        "penalty", "probe", "raid", "sebi notice", "usfda oai", "warning letter", 
        "fire", "strike", "resigns", "downgrade", "fraud", "scam", "tax notice", "inquiry"
    ]
    
    if any(k in t for k in pos_keys):
        return "🟢 POSITIVE IMPACT", 1
    elif any(k in t for k in neg_keys):
        return "🔴 NEGATIVE IMPACT", -1
    return "⚪ NEUTRAL / GENERAL", 0

def fetch_rss_feed(query, limit=15):
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
                
                matched_stock = "MARKET"
                for stk in ALL_FNO_STOCKS:
                    if stk.lower() in title.lower():
                        matched_stock = stk
                        break
                
                results.append({
                    "stock": matched_stock,
                    "title": title,
                    "link": link,
                    "date": date
                })
    except Exception:
        pass
    return results

def fetch_stock_specific(stock, context_type):
    if context_type == "tv":
        query = f"{stock}+share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi+OR+target)"
    elif context_type == "brokerage":
        query = f"{stock}+share+target+price+OR+{stock}+brokerage+rating"
    elif context_type == "results":
        query = f"{stock}+quarterly+results+OR+{stock}+pat+OR+{stock}+net+profit+OR+{stock}+earnings"
    elif context_type == "impact_news":
        query = f"{stock}+order+OR+{stock}+sebi+OR+{stock}+usfda+OR+{stock}+penalty+OR+{stock}+approval"
    else:
        query = f"{stock}+share+India"
    return fetch_rss_feed(query, limit=6)

# ================= 3. UI Tabs =================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Earnings Verdict",
    "⚡ High-Impact News",
    "📺 TV Research Calls",
    "🎯 Brokerage Targets", 
    "🚀 Sector & Market Pulse", 
    "🐦 Twitter / X Pulse"
])

# ================= TAB 1: Earnings Verdict =================
with tab1:
    st.subheader("📊 Corporate Results: Bullish vs. Bearish Verdict")
    st.caption("Automated financial results scanner evaluating profitability, revenue, and analyst estimates:")
    
    if st.button("🔄 Auto-Scan Latest Results & Verdicts", use_container_width=True, key="btn_res_verdict"):
        with st.spinner("Analyzing recent earnings reports..."):
            res_items = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=25)
            if res_items:
                for item in res_items:
                    verdict, desc = analyze_earnings_verdict(item["title"])
                    st.markdown(f"**[{verdict}]** `{item['stock']}` — *{desc}*")
                    st.markdown(f"[{item['title']}]({item['link']})")
                    st.caption(f"Published: {item['date']}")
                    st.divider()
            else:
                st.info("No recent corporate earnings updates found.")

    st.write("---")
    st.subheader("🔍 Look Up Specific Stock Results")
    target_res_stk = st.selectbox("Select F&O Stock:", ALL_FNO_STOCKS, key="box_res_stk")
    if st.button(f"Analyze Results for {target_res_stk}", use_container_width=True):
        single_res = fetch_stock_specific(target_res_stk, "results")
        if single_res:
            for sr in single_res:
                v, d = analyze_earnings_verdict(sr["title"])
                st.markdown(f"**[{v}]** [{sr['title']}]({sr['link']})")
                st.caption(f"Date: {sr['date']}")
        else:
            st.info(f"No recent quarterly announcements found for {target_res_stk}.")

# ================= TAB 2: High-Impact News =================
with tab2:
    st.subheader("⚡ High-Impact Market Movers")
    st.caption("Real-time scan for SEBI orders, contract wins, USFDA observations, and management changes:")
    
    if st.button("🔄 Load All Market-Moving Headlines", use_container_width=True, key="btn_impact_news"):
        with st.spinner("Filtering high-impact events..."):
            news_items = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda+OR+acquisition+OR+resigns)+share+India", limit=25)
            if news_items:
                for n in news_items:
                    impact_tag, _ = analyze_news_impact(n["title"])
                    st.markdown(f"**[{impact_tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.caption(f"Time: {n['date']}")
                    st.divider()
            else:
                st.info("No critical corporate action headlines detected.")

    st.write("---")
    st.subheader("🔍 Search Stock-Specific Critical News")
    target_n_stk = st.selectbox("Select F&O Stock:", ALL_FNO_STOCKS, key="box_news_stk")
    if st.button(f"Fetch Breaking News for {target_n_stk}", use_container_width=True):
        single_n = fetch_stock_specific(target_n_stk, "impact_news")
        if single_n:
            for sn in single_n:
                tag, _ = analyze_news_impact(sn["title"])
                st.markdown(f"**[{tag}]** [{sn['title']}]({sn['link']})")
                st.caption(f"Date: {sn['date']}")
        else:
            st.info(f"No critical headlines found for {target_n_stk}.")

# ================= TAB 3: Zee Business & CNBC Awaaz =================
with tab3:
    st.subheader("📺 Business TV Recommendations (Automated Feed)")
    st.caption("Live panelist picks and segment highlights from Zee Business and CNBC Awaaz:")
    
    if st.button("🔄 Auto-Scan TV Calls", use_container_width=True, key="btn_tv_auto"):
        with st.spinner("Aggregating TV broadcast research..."):
            auto_tv = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=20)
            if auto_tv:
                for item in auto_tv:
                    ch_tag = "🟢 Zee Business" if "zee" in item["title"].lower() else ("🔵 CNBC Awaaz" if "cnbc" in item["title"].lower() or "awaaz" in item["title"].lower() else "📺 Business TV")
                    st.markdown(f"**[{ch_tag}]** `{item['stock']}` | [{item['title']}]({item['link']})")
                    st.caption(f"Time: {item['date']}")
                    st.divider()
            else:
                st.info("No recent TV recommendations found.")

    st.write("---")
    st.subheader("🔍 Search TV History by Stock")
    single_tv_stock = st.selectbox("Select F&O Stock:", ALL_FNO_STOCKS, key="box_tv_single")
    if st.button(f"Fetch TV Research for {single_tv_stock}", use_container_width=True):
        res = fetch_stock_specific(single_tv_stock, "tv")
        if res:
            for r in res:
                st.markdown(f"• [{r['title']}]({r['link']})")
                st.caption(f"Date: {r['date']}")
        else:
            st.info(f"No specific TV channel coverage found for {single_tv_stock}.")

# ================= TAB 4: Brokerage Targets =================
with tab4:
    st.subheader("🎯 Institutional Brokerage Ratings & Targets")
    st.caption("Upgrades, downgrades, and price targets from Morgan Stanley, Jefferies, CLSA, and domestic houses:")
    
    if st.button("🔄 Auto-Scan Brokerage Targets", use_container_width=True, key="btn_brok_auto"):
        with st.spinner("Processing analyst target changes..."):
            auto_brok = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=20)
            if auto_brok:
                for b in auto_brok:
                    t_low = b["title"].lower()
                    call = "🟢 BUY / TARGET UP" if any(w in t_low for w in ["buy", "raised", "upgrade", "bullish", "overweight"]) else ("🔴 SELL / TARGET CUT" if any(w in t_low for w in ["sell", "cut", "downgrade", "bearish", "underweight"]) else "⚪ TARGET UPDATE")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.caption(f"Time: {b['date']}")
                    st.divider()
            else:
                st.info("No analyst target updates detected.")

    st.write("---")
    st.subheader("🔍 Look Up Brokerage Targets for a Stock")
    single_brok_stock = st.selectbox("Select F&O Stock:", ALL_FNO_STOCKS, key="box_brok_single")
    if st.button(f"Check Targets for {single_brok_stock}", use_container_width=True):
        res = fetch_stock_specific(single_brok_stock, "brokerage")
        if res:
            for r in res:
                st.markdown(f"• [{r['title']}]({r['link']})")
                st.caption(f"Date: {r['date']}")
        else:
            st.info(f"No active brokerage targets found for {single_brok_stock}.")

# ================= TAB 5: Sector & Market Pulse =================
with tab5:
    st.subheader("🌐 Sector Strength & Sentiment Scanner")
    if st.button("📊 Scan Sector Sentiment & Top F&O Movers", use_container_width=True, key="btn_mkt_scan"):
        with st.spinner("Scanning 35 key F&O stocks across sectors..."):
            all_data = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = executor.map(lambda s: fetch_stock_specific(s, "general"), ALL_FNO_STOCKS[:35])
                for r_list in results:
                    all_data.extend(r_list)

            if all_data:
                df = pd.DataFrame(all_data)
                df["sector"] = df["stock"].map(STOCK_SECTOR_MAP).fillna("Other")
                
                def quick_score(t):
                    tl = t.lower()
                    if any(w in tl for w in ["surge", "gain", "profit", "jump", "rally", "buy", "up"]): return 1
                    if any(w in tl for w in ["fall", "crash", "loss", "drop", "down", "sell"]): return -1
                    return 0
                df["score"] = df["title"].apply(quick_score)

                # Sector Overview
                sec_df = df.groupby("sector")["score"].sum().reset_index().sort_values(by="score", ascending=False)
                sec_df["Trend"] = sec_df["score"].apply(lambda s: "🟢 Strong" if s > 0 else ("🔴 Weak" if s < 0 else "⚪ Neutral"))
                
                st.write("### 🏢 Sector Sentiment Breakdown")
                st.dataframe(sec_df.rename(columns={"sector": "Sector", "score": "Net Score"}), use_container_width=True, hide_index=True)

                st.divider()

                # Stock Movers
                stk_df = df.groupby(["stock", "sector"])["score"].sum().reset_index().sort_values(by="score", ascending=False)
                c1, c2 = st.columns(2)
                with c1:
                    st.success("🟢 **Top Bullish Stocks**")
                    st.dataframe(stk_df[stk_df["score"] > 0].head(8).rename(columns={"stock": "Stock", "sector": "Sector", "score": "Score"}), use_container_width=True, hide_index=True)
                with c2:
                    st.error("🔴 **Top Bearish Stocks**")
                    st.dataframe(stk_df[stk_df["score"] < 0].tail(8).rename(columns={"stock": "Stock", "sector": "Sector", "score": "Score"}), use_container_width=True, hide_index=True)

# ================= TAB 6: Twitter / X Pulse =================
with tab6:
    st.subheader("🐦 Social Media Breakout Buzz (X / Twitter)")
    if st.button("🔄 Auto-Scan Breakout Buzz", use_container_width=True, key="btn_tw_auto"):
        with st.spinner("Tracking community chatter and momentum calls..."):
            auto_tw = fetch_rss_feed("stock+breakout+OR+multibagger+twitter+India", limit=15)
            if auto_tw:
                for tw in auto_tw:
                    st.markdown(f"• `{tw['stock']}` | [{tw['title']}]({tw['link']})")
                    st.divider()
            else:
                st.info("No trending breakout chatter identified.")
