import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="F&O Master 360",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("⚡ F&O Master 360")
st.caption("F&O स्टॉक्स: टीवी चैनल रिसर्च (Zee Business / CNBC Awaaz), सेंटिमेंट, Twitter व अर्निंग्स")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 180+ F&O स्टॉक्स की सूची =================
ALL_FNO_STOCKS = sorted([
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS",
    "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL",
    "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT",
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT",
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL",
    "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR",
    "DELHIVERY", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND",
    "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES",
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI",
    "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART",
    "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL",
    "JKCEMENT", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN",
    "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI",
    "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MOTILALOFS", "MPHASIS", "MRF",
    "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC",
    "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PAYTM", "PEL", "PERSISTENT", "PETRONET",
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POONAWALLA", "POWERGRID", "PVRINOX",
    "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN",
    "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM",
    "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM",
    "TITAN", "TORNTPHARM", "TORNTPOWER", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO",
    "UPL", "VEDL", "VOLTAS", "WIPRO", "ZYDUSLIFE"
])

# ================= सेंटिमेंट इंजन =================
def evaluate_sentiment(text):
    text_lower = text.lower()
    pos_words = ["surge", "gain", "profit", "jump", "rally", "beat", "bull", "buy", "growth", "target", "खरीदारी"]
    neg_words = ["fall", "crash", "loss", "plunge", "drop", "probe", "down", "bear", "sell", "बिकवाली", "नुकसान"]
    
    pos = sum(1 for w in pos_words if w in text_lower)
    neg = sum(1 for w in neg_words if w in text_lower)
    
    if pos > neg:
        return "POSITIVE", 1
    elif neg > pos:
        return "NEGATIVE", -1
    return "NEUTRAL", 0

# ================= डेटा फेचर्स =================
def fetch_stock_intel(stock):
    query = f"{stock}+share+India"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    items = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:3]:
                title = entry.find("title").text
                link = entry.find("link").text
                date = entry.find("pubDate").text
                sent_label, sent_val = evaluate_sentiment(title)
                items.append({
                    "stock": stock,
                    "title": title,
                    "link": link,
                    "date": date,
                    "sentiment": sent_label,
                    "score": sent_val
                })
    except Exception:
        pass
    return items

def fetch_tv_channel_research(stock):
    # Zee Business & CNBC Awaaz विशिष्ट फ़िल्टर
    query = f"{stock}+share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi+OR+target)"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    tv_calls = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:6]:
                title = entry.find("title").text
                link = entry.find("link").text
                date = entry.find("pubDate").text
                
                source_tag = "📺 TV रिसर्च"
                if "zee" in title.lower() or "zee business" in title.lower():
                    source_tag = "🟢 Zee Business"
                elif "cnbc" in title.lower() or "awaaz" in title.lower():
                    source_tag = "🔵 CNBC Awaaz"
                    
                tv_calls.append({
                    "source": source_tag,
                    "headline": title,
                    "link": link,
                    "date": date
                })
    except Exception:
        pass
    return tv_calls

def fetch_brokerage_targets(stock):
    query = f"{stock}+share+target+price+OR+{stock}+brokerage+rating"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    targets = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:5]:
                title = entry.find("title").text
                link = entry.find("link").text
                date = entry.find("pubDate").text
                
                title_lower = title.lower()
                if any(w in title_lower for w in ["buy", "upgrade", "bullish"]):
                    call_type = "🟢 BUY / UPGRADE"
                elif any(w in title_lower for w in ["sell", "downgrade", "bearish"]):
                    call_type = "🔴 SELL / DOWNGRADE"
                else:
                    call_type = "⚪ HOLD / NEUTRAL"

                targets.append({
                    "call": call_type,
                    "headline": title,
                    "link": link,
                    "date": date
                })
    except Exception:
        pass
    return targets

def fetch_corporate_results(stock):
    query = f"{stock}+quarterly+results+OR+{stock}+board+meeting"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:4]:
                results.append({
                    "title": entry.find("title").text,
                    "link": entry.find("link").text,
                    "date": entry.find("pubDate").text
                })
    except Exception:
        pass
    return results

def fetch_twitter_pulse(stock):
    query = f"{stock}+stock+twitter+OR+{stock}+breakout"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    tweets = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:4]:
                tweets.append({
                    "post": entry.find("title").text,
                    "link": entry.find("link").text
                })
    except Exception:
        pass
    return tweets

# ================= 6-टैब मोबाइल डैशबोर्ड =================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📺 Zee/CNBC कॉल्स",
    "🚀 त्वरित स्कैनर", 
    "🎯 ब्रोकरेज टारगेट्स", 
    "📅 रिजल्ट्स कैलेंडर", 
    "🐦 Twitter पल्स", 
    "📰 स्टॉक न्यूज़"
])

# ---- TAB 1: Zee Business और CNBC Awaaz रिसर्च ----
with tab1:
    st.subheader("📺 Zee Business & CNBC Awaaz रिसर्च कॉल्स")
    tv_stock = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="tv_box")
    
    if st.button(f"{tv_stock} की टीवी सिफारिशें निकालें", use_container_width=True):
        with st.spinner(f"Zee Business व CNBC Awaaz से {tv_stock} का डेटा आ रहा है..."):
            tv_data = fetch_tv_channel_research(tv_stock)
            if tv_data:
                for item in tv_data:
                    st.markdown(f"**[{item['source']}]** [{item['headline']}]({item['link']})")
                    st.caption(f"समय: {item['date']}")
                    st.divider()
            else:
                st.info("इस शेयर पर हाल ही में कोई टीवी रिसर्च कवरेज नहीं मिली।")

# ---- TAB 2: त्वरित स्कैनर ----
with tab1_alt := tab2:
    st.subheader("🔥 F&O टॉप मूवर्स व सेंटिमेंट")
    scan_limit = st.slider("कितने स्टॉक्स स्कैन करें?", min_value=20, max_value=len(ALL_FNO_STOCKS), value=30, step=10)
    
    if st.button("मार्केट स्कैन शुरू करें", use_container_width=True):
        stocks_to_scan = ALL_FNO_STOCKS[:scan_limit]
        with st.spinner(f"{scan_limit} F&O स्टॉक्स स्कैन हो रहे हैं..."):
            all_data = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = executor.map(fetch_stock_intel, stocks_to_scan)
                for res in results:
                    all_data.extend(res)
            
            if all_data:
                df = pd.DataFrame(all_data)
                summary = df.groupby("stock")["score"].sum().reset_index().sort_values(by="score", ascending=False)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.success("🟢 **शीर्ष बुलिश स्टॉक्स**")
                    st.dataframe(summary[summary["score"] > 0].head(8).rename(columns={"stock": "शेयर", "score": "स्कोर"}), use_container_width=True, hide_index=True)
                with col2:
                    st.error("🔴 **शीर्ष बेयरिश स्टॉक्स**")
                    st.dataframe(summary[summary["score"] < 0].tail(8).rename(columns={"stock": "शेयर", "score": "स्कोर"}), use_container_width=True, hide_index=True)

# ---- TAB 3: ब्रोकरेज टारगेट्स ----
with tab3:
    st.subheader("🎯 रिसर्च हाउस टारगेट प्राइस")
    target_stock = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="target_box")
    if st.button(f"{target_stock} के टारगेट्स देखें", use_container_width=True):
        with st.spinner("टारगेट्स लोड हो रहे हैं..."):
            b_data = fetch_brokerage_targets(target_stock)
            if b_data:
                for b in b_data:
                    st.markdown(f"**[{b['call']}]** [{b['headline']}]({b['link']})")
                    st.caption(f"तारीख: {b['date']}")
                    st.divider()

# ---- TAB 4: रिजल्ट्स कैलेंडर ----
with tab4:
    st.subheader("📅 अर्निंग्स व बोर्ड मीटिंग्स")
    res_stock = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="res_box")
    if st.button(f"{res_stock} के नतीजे देखें", use_container_width=True):
        with st.spinner("रिजल्ट कैलेंडर लोड हो रहा है..."):
            r_data = fetch_corporate_results(res_stock)
            if r_data:
                for r in r_data:
                    st.markdown(f"📌 [{r['title']}]({r['link']})")
                    st.caption(f"समय: {r['date']}")
                    st.divider()

# ---- TAB 5: Twitter पल्स ----
with tab5:
    st.subheader("🐦 सोशल व ब्रेकआउट चर्चा")
    tw_target = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="tw_box")
    if st.button(f"{tw_target} का सोशल ट्रेंड देखें", use_container_width=True):
        with st.spinner("Twitter चर्चाएँ लोड हो रही हैं..."):
            tweets = fetch_twitter_pulse(tw_target)
            if tweets:
                for t in tweets:
                    st.markdown(f"• [{t['post']}]({t['link']})")

# ---- TAB 6: स्टॉक न्यूज़ ----
with tab6:
    st.subheader("📰 विस्तृत मीडिया रिपोर्ट्स")
    s_stock = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="news_box")
    if st.button(f"{s_stock} की हेडलाइंस निकालें", use_container_width=True):
        with st.spinner("ख़बरें लोड हो रही हैं..."):
            n_data = fetch_stock_intel(s_stock)
            if n_data:
                for n in n_data:
                    tag = "🟢 POSITIVE" if n["sentiment"] == "POSITIVE" else ("🔴 NEGATIVE" if n["sentiment"] == "NEGATIVE" else "⚪ NEUTRAL")
                    st.markdown(f"**{tag}** | [{n['title']}]({n['link']})")
                    st.caption(f"समय: {n['date']}")
                    st.divider()
