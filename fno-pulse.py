import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(
    page_title="F&O Master 360",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 F&O Master 360")
st.caption("180+ F&O स्टॉक्स का लाइव न्यूज़, सोशल सेंटिमेंट व कॉर्पोरेट रिजल्ट्स ट्रैकर")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 180+ F&O स्टॉक्स की मुकम्मल लिस्ट =================
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

# ================= 1. सेंटिमेंट इंजन =================
def evaluate_sentiment(text):
    text_lower = text.lower()
    pos_words = ["surge", "gain", "profit", "jump", "rally", "beat", "bull", "buy", "growth", "high", "dividend", "up"]
    neg_words = ["fall", "crash", "loss", "plunge", "drop", "probe", "down", "bear", "sell", "penalty", "miss", "fraud"]
    
    pos = sum(1 for w in pos_words if w in text_lower)
    neg = sum(1 for w in neg_words if w in text_lower)
    
    if pos > neg:
        return "POSITIVE", 1
    elif neg > pos:
        return "NEGATIVE", -1
    return "NEUTRAL", 0

# ================= 2. डेटा फेचर्स =================
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

def fetch_corporate_results(stock):
    query = f"{stock}+quarterly+results+OR+{stock}+board+meeting+date"
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
                title = entry.find("title").text
                link = entry.find("link").text
                sent_label, _ = evaluate_sentiment(title)
                tweets.append({
                    "post": title,
                    "link": link,
                    "sent": sent_label
                })
    except Exception:
        pass
    return tweets

# ================= 3. मोबाइल-फ्रेंडली टैब इंटरफ़ेस =================
tab1, tab2, tab3, tab4 = st.tabs(["🚀 त्वरित स्कैनर", "📅 रिजल्ट्स कैलेंडर", "📰 स्टॉक रिपोर्ट्स", "🐦 सोशल पल्स"])

# ---- TAB 1: त्वरित मार्केट स्कैनर ----
with tab1:
    st.subheader("🔥 F&O टॉप मूवर्स व सेंटिमेंट")
    scan_limit = st.slider("कितने लिक्विड स्टॉक्स स्कैन करें?", min_value=20, max_value=len(ALL_FNO_STOCKS), value=35, step=15)
    
    if st.button("बाज़ार सेंटिमेंट स्कैन करें", use_container_width=True):
        stocks_to_scan = ALL_FNO_STOCKS[:scan_limit]
        with st.spinner(f"{scan_limit} F&O स्टॉक्स का डेटा प्रोसेस हो रहा है..."):
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
                    top_bulls = summary[summary["score"] > 0].head(8)
                    st.dataframe(top_bulls.rename(columns={"stock": "शेयर", "score": "स्कोर"}), use_container_width=True, hide_index=True)
                with col2:
                    st.error("🔴 **शीर्ष बेयरिश स्टॉक्स**")
                    top_bears = summary[summary["score"] < 0].tail(8)
                    st.dataframe(top_bears.rename(columns={"stock": "शेयर", "score": "स्कोर"}), use_container_width=True, hide_index=True)
            else:
                st.warning("डेटा फेच नहीं हो पाया।")

# ---- TAB 2: कॉर्पोरेट रिजल्ट्स व बोर्ड मीटिंग्स ----
with tab2:
    st.subheader("📅 अर्निंग्स व बोर्ड मीटिंग ट्रैकर")
    target_stock = st.selectbox("नतीजे चेक करने के लिए शेयर चुनें:", ALL_FNO_STOCKS, key="res_box")
    
    if st.button(f"{target_stock} का रिजल्ट अपडेट देखें", use_container_width=True):
        with st.spinner("रिजल्ट कैलेंडर और घोषणाएँ लोड हो रही हैं..."):
            res_data = fetch_corporate_results(target_stock)
            if res_data:
                for r in res_data:
                    st.markdown(f"📌 **[{r['title']}]({r['link']})**")
                    st.caption(f"अपडेट समय: {r['date']}")
                    st.divider()
            else:
                st.info("इस शेयर के लिए कोई हालिया रिजल्ट घोषणा नहीं मिली।")

# ---- TAB 3: सिंगल स्टॉक न्यूज़ ----
with tab3:
    st.subheader("📰 विस्तृत न्यूज़ व ब्रोकरेज रिपोर्ट्स")
    s_stock = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="rep_box")
    
    if st.button(f"{s_stock} की रिपोर्ट्स निकालें", use_container_width=True):
        with st.spinner("ख़बरें लोड हो रही हैं..."):
            news = fetch_stock_intel(s_stock)
            if news:
                for n in news:
                    tag = "🟢 POSITIVE" if n["sentiment"] == "POSITIVE" else ("🔴 NEGATIVE" if n["sentiment"] == "NEGATIVE" else "⚪ NEUTRAL")
                    st.markdown(f"**{tag}** | [{n['title']}]({n['link']})")
                    st.caption(f"समय: {n['date']}")
                    st.divider()
            else:
                st.info("कोई ताज़ा ख़बर नहीं मिली।")

# ---- TAB 4: ट्विटर / सोशल पल्स ----
with tab4:
    st.subheader("🐦 सोशल चर्चा व ब्रेकआउट कॉल्स")
    tw_target = st.selectbox("शेयर चुनें:", ALL_FNO_STOCKS, key="tw_box")
    
    if st.button(f"{tw_target} का सोशल ट्रेंड देखें", use_container_width=True):
        with st.spinner("सोशल ट्रेंड्स स्कैन हो रहे हैं..."):
            social = fetch_twitter_pulse(tw_target)
            if social:
                for s in social:
                    badge = "🟢 बुलिश" if s["sent"] == "POSITIVE" else "⚪ सामान्य"
                    st.markdown(f"• **[{badge}]** [{s['post']}]({s['link']})")
            else:
                st.info("सोशल मीडिया पर कोई ताज़ा गतिविधि नहीं मिली।")
