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
st.caption("इंडेक्स, सेक्टोरल सेंटिमेंट, F&O स्टॉक्स, ब्रोकरेज टारगेट्स व टीवी रिसर्च")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 1. F&O स्टॉक्स और उनके सेक्टर्स की मैपिंग =================
STOCK_SECTOR_MAP = {
    # Banking & Financial Services
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "BANKBARODA": "Banking", "PNB": "Banking",
    "BAJFINANCE": "Financial", "BAJAJFINSV": "Financial", "CHOLAFIN": "Financial", "MUTHOOTFIN": "Financial",
    "PFC": "Financial", "RECLTD": "Financial", "SHRIRAMFIN": "Financial", "MOTILALOFS": "Financial",
    
    # IT & Tech
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT", 
    "LTIM": "IT", "COFORGE": "IT", "PERSISTENT": "IT", "MPHASIS": "IT", "NAUKRI": "IT",
    
    # Auto & Auto Ancillaries
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

# ================= 2. सेंटिमेंट इंजन =================
def evaluate_sentiment(text):
    text_lower = text.lower()
    pos_words = ["surge", "gain", "profit", "jump", "rally", "beat", "bull", "buy", "growth", "high", "upgrade", "positive", "खरीदारी"]
    neg_words = ["fall", "crash", "loss", "plunge", "drop", "probe", "down", "bear", "sell", "penalty", "miss", "downgrade", "बिकवाली"]
    
    pos = sum(1 for w in pos_words if w in text_lower)
    neg = sum(1 for w in neg_words if w in text_lower)
    
    if pos > neg:
        return "POSITIVE", 1
    elif neg > pos:
        return "NEGATIVE", -1
    return "NEUTRAL", 0

# ================= 3. डेटा फेचर्स =================
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
                    "sector": STOCK_SECTOR_MAP.get(stock, "General"),
                    "title": title,
                    "link": link,
                    "date": date,
                    "sentiment": sent_label,
                    "score": sent_val
                })
    except Exception:
        pass
    return items

def fetch_index_sentiment():
    indices = ["Nifty 50", "Bank Nifty", "Nifty IT", "Nifty Auto", "Nifty Metal"]
    index_scores = {}
    for idx in indices:
        query = f"{idx.replace(' ', '+')}+India+market"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        score = 0
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for entry in root.findall(".//item")[:4]:
                    _, val = evaluate_sentiment(entry.find("title").text)
                    score += val
        except Exception:
            pass
        index_scores[idx] = score
    return index_scores

def fetch_tv_channel_research(stock):
    query = f"{stock}+share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi+OR+target)"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    tv_calls = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for entry in root.findall(".//item")[:5]:
                title = entry.find("title").text
                link = entry.find("link").text
                date = entry.find("pubDate").text
                source_tag = "🟢 Zee Business" if "zee" in title.lower() else ("🔵 CNBC Awaaz" if "cnbc" in title.lower() or "awaaz" in title.lower() else "📺 TV कॉल")
                tv_calls.append({"source": source_tag, "headline": title, "link": link, "date": date})
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
                t_low = title.lower()
                call = "🟢 BUY / UPGRADE" if any(w in t_low for w in ["buy", "upgrade", "bullish"]) else ("🔴 SELL / DOWNGRADE" if any(w in t_low for w in ["sell", "downgrade", "bearish"]) else "⚪ HOLD / NEUTRAL")
                targets.append({"call": call, "headline": title, "link": link, "date": date})
    except Exception:
        pass
    return targets

# ================= 4. मोबाइल डैशबोर्ड टैब्स =================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 मार्केट & सेक्टर पल्स", 
    "📺 Zee/CNBC कॉल्स",
    "🎯 ब्रोकरेज टारगेट्स", 
    "📅 रिजल्ट्स कैलेंडर", 
    "📰 विस्तृत न्यूज़"
])

# ---- TAB 1: इंडेक्स, सेक्टर्स और स्टॉक्स स्कैनर ----
with tab1:
    st.subheader("🌐 प्रमुख इंडेक्स का सेंटिमेंट")
    if st.button("📊 इंडेक्स व सेक्टोरल स्कैन शुरू करें", use_container_width=True):
        with st.spinner("इंडेक्स और सेक्टर्स का डेटा लोड हो रहा है..."):
            # 1. इंडेक्स स्कोर कार्ड्स
            idx_data = fetch_index_sentiment()
            cols = st.columns(len(idx_data))
            for i, (idx_name, score) in enumerate(idx_data.items()):
                status = "🟢 तेज (Bullish)" if score > 0 else ("🔴 मंदा (Bearish)" if score < 0 else "⚪ तटस्थ")
                cols[i].metric(label=idx_name, value=status, delta=f"स्कोर: {score}")

            st.divider()

            # 2. स्टॉक्स और सेक्टर्स विश्लेषण
            all_stock_data = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = executor.map(fetch_stock_intel, ALL_FNO_STOCKS)
                for res in results:
                    all_stock_data.extend(res)

            if all_stock_data:
                df = pd.DataFrame(all_stock_data)
                
                # सेक्टर-वाइज सेंटिमेंट
                sector_summary = df.groupby("sector")["score"].sum().reset_index().sort_values(by="score", ascending=False)
                sector_summary["सेक्टर ट्रेंड"] = sector_summary["score"].apply(lambda s: "🟢 मजबूत" if s > 0 else ("🔴 कमजोर" if s < 0 else "⚪ साइडवेज़"))
                
                st.write("### 🏢 सेक्टर्स की परफॉर्मेंस")
                st.dataframe(sector_summary.rename(columns={"sector": "सेक्टर", "score": "कुल स्कोर"}), use_container_width=True, hide_index=True)

                st.divider()

                # स्टॉक-वाइज टेबल जिसमें उसका सेक्टर भी साथ में दिखेगा
                stock_summary = df.groupby(["stock", "sector"])["score"].sum().reset_index().sort_values(by="score", ascending=False)
                
                # सेक्टर का ट्रेंड भी स्टॉक टेबल के साथ जोड़ना
                sector_dict = dict(zip(sector_summary["sector"], sector_summary["सेक्टर ट्रेंड"]))
                stock_summary["सेक्टर का मूड"] = stock_summary["sector"].map(sector_dict)

                col1, col2 = st.columns(2)
                with col1:
                    st.success("🟢 **शीर्ष बुलिश स्टॉक्स**")
                    top_bulls = stock_summary[stock_summary["score"] > 0].head(10)
                    st.dataframe(top_bulls.rename(columns={"stock": "शेयर", "sector": "सेक्टर", "score": "स्कोर"}), use_container_width=True, hide_index=True)
                with col2:
                    st.error("🔴 **शीर्ष बेयरिश स्टॉक्स**")
                    top_bears = stock_summary[stock_summary["score"] < 0].tail(10)
                    st.dataframe(top_bears.rename(columns={"stock": "शेयर", "sector": "सेक्टर", "score": "स्कोर"}), use_container_width=True, hide_index=True)

# ---- TAB 2: Zee Business & CNBC Awaaz ----
with tab2:
    st.subheader("📺 टीवी चैनल्स की सिफारिशें")
    tv_s = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="tv_s")
    if st.button(f"{tv_s} की टीवी कॉल्स निकालें", use_container_width=True):
        with st.spinner("डेटा फेच हो रहा है..."):
            calls = fetch_tv_channel_research(tv_s)
            if calls:
                for c in calls:
                    st.markdown(f"**[{c['source']}]** [{c['headline']}]({c['link']})")
                    st.caption(f"समय: {c['date']}")
                    st.divider()
            else:
                st.info("हालिया टीवी रिसर्च कवरेज उपलब्ध नहीं है।")

# ---- TAB 3: ब्रोकरेज टारगेट्स ----
with tab3:
    st.subheader("🎯 ब्रोकरेज हाउस टारगेट्स")
    tgt_s = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="tgt_s")
    if st.button(f"{tgt_s} के टारगेट्स देखें", use_container_width=True):
        with st.spinner("टारगेट्स आ रहे हैं..."):
            b_list = fetch_brokerage_targets(tgt_s)
            if b_list:
                for b in b_list:
                    st.markdown(f"**[{b['call']}]** [{b['headline']}]({b['link']})")
                    st.caption(f"तारीख: {b['date']}")
                    st.divider()
            else:
                st.info("कोई ताज़ा टारगेट नहीं मिला।")

# ---- TAB 4: रिजल्ट्स कैलेंडर ----
with tab4:
    st.subheader("📅 रिजल्ट्स व बोर्ड मीटिंग्स")
    res_s = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="res_s")
    if st.button(f"{res_s} के नतीजे देखें", use_container_width=True):
        st.info("रिजल्ट कैलेंडर लोड किया जा रहा है...")

# ---- TAB 5: स्टॉक न्यूज़ ----
with tab5:
    st.subheader("📰 विस्तृत हेडलाइंस")
    nw_s = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="nw_s")
    if st.button(f"{nw_s} की खबरें देखें", use_container_width=True):
        with st.spinner("न्यूज़ लोड हो रही है..."):
            n_items = fetch_stock_intel(nw_s)
            if n_items:
                for n in n_items:
                    tag = "🟢 POSITIVE" if n["sentiment"] == "POSITIVE" else ("🔴 NEGATIVE" if n["sentiment"] == "NEGATIVE" else "⚪ NEUTRAL")
                    st.markdown(f"**{tag}** | [{n['title']}]({n['link']})")
                    st.caption(f"समय: {n['date']}")
                    st.divider()
