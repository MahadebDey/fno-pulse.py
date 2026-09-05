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
st.caption("ऑटोमैटिक कॉर्पोरेट रिज़ल्ट्स (Bullish/Bearish वर्डिक्ट), हाई-इम्पैक्ट न्यूज़, टीवी कॉल्स व ब्रोकरेज टारगेट्स")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 1. F&O स्टॉक्स व सेक्टर्स की मास्टर मैपिंग =================
STOCK_SECTOR_MAP = {
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "BANKBARODA": "Banking", "PNB": "Banking",
    "BAJFINANCE": "Financial", "BAJAJFINSV": "Financial", "CHOLAFIN": "Financial", "MUTHOOTFIN": "Financial",
    "PFC": "Financial", "RECLTD": "Financial", "SHRIRAMFIN": "Financial", "MOTILALOFS": "Financial",
    "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT", 
    "LTIM": "IT", "COFORGE": "IT", "PERSISTENT": "IT", "MPHASIS": "IT", "NAUKRI": "IT",
    "TATAMOTORS": "Auto", "MARUTI": "Auto", "M&M": "Auto", "BAJAJ-AUTO": "Auto", 
    "HEROMOTOCO": "Auto", "EICHERMOT": "Auto", "TVSMOTOR": "Auto", "BHARATFORG": "Auto", 
    "APOLLOTYRE": "Auto", "BALKRISIND": "Auto", "MOTHERSON": "Auto",
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals", "JINDALSTEL": "Metals", 
    "VEDL": "Metals", "COALINDIA": "Metals", "NMDC": "Metals", "NATIONALUM": "Metals", "SAIL": "Metals",
    "RELIANCE": "Energy/Oil", "BPCL": "Energy/Oil", "IOC": "Energy/Oil", "ONGC": "Energy/Oil", 
    "NTPC": "Power", "POWERGRID": "Power", "TATAPOWER": "Power", "ADANIENT": "Energy", "ADANIPORTS": "Infra",
    "SUNPHARMA": "Pharma", "CIPLA": "Pharma", "DRREDDY": "Pharma", "DIVISLAB": "Pharma", 
    "LUPIN": "Pharma", "AUROPHARMA": "Pharma", "APOLLOHOSP": "Pharma", "ZYDUSLIFE": "Pharma",
    "ITC": "FMCG", "HINDUNILVR": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG", 
    "DABUR": "FMCG", "TATACONSUM": "FMCG", "TITAN": "Consumer", "ASIANPAINT": "Consumer",
    "LT": "Infra", "ULTRACEMCO": "Cement", "GRASIM": "Cement", "AMBUJACEM": "Cement", 
    "POLYCAB": "Cables", "HAVELLS": "Consumer Elec", "DIXON": "Electronics", "DLF": "Realty"
}

ALL_FNO_STOCKS = sorted(list(STOCK_SECTOR_MAP.keys()))

# ================= 2. रिज़ल्ट व न्यूज़ रिसर्च इंजन =================
def analyze_earnings_verdict(text):
    t = text.lower()
    # बुलिश नतीजे के संकेत
    bull_keys = ["profit jumps", "pat rises", "net profit up", "beats estimates", "beat estimates", 
                 "revenue up", "margin expands", "dividend declared", "strong q", "robust growth", 
                 "ebitda jumps", "guidance raised", "quarterly profit surges"]
    # बेयरिश नतीजे के संकेत
    bear_keys = ["profit falls", "pat drops", "net loss", "misses estimates", "miss estimates", 
                 "margin drops", "ebitda falls", "slumps", "plunges", "weak q", "guidance cut", 
                 "down 10%", "down 15%", "revenue declines"]
    
    is_bull = any(k in t for k in bull_keys)
    is_bear = any(k in t for k in bear_keys)
    
    if is_bull and not is_bear:
        return "🟢 BULLISH RESULT", "शानदार नतीजे / अनुमान से बेहतर"
    elif is_bear and not is_bull:
        return "🔴 BEARISH RESULT", "कमज़ोर नतीजे / घाटा / मार्जिन दबाव"
    return "⚪ RESULT UPDATE", "नतीजों की घोषणा / सामान्य"

def analyze_news_impact(text):
    t = text.lower()
    pos_keys = ["bags order", "wins contract", "approval", "acquires", "upgrade", "joint venture", 
                "expansion", "commissioned", "target raised", "surges", "green signal"]
    neg_keys = ["penalty", "probe", "raid", "sebi notice", "usfda oai", "warning letter", 
                "fire", "strike", "resigns", "downgrade", "fraud", "scam", "tax notice"]
    
    if any(k in t for k in pos_keys):
        return "🟢 POSITIVE NEWS", 1
    elif any(k in t for k in neg_keys):
        return "🔴 NEGATIVE NEWS", -1
    return "⚪ GENERAL NEWS", 0

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

# ================= 3. मोबाइल-फ्रेंडली टैब डैशबोर्ड =================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 रिज़ल्ट्स वर्डिक्ट",
    "⚡ हाई-इम्पैक्ट न्यूज़",
    "📺 Zee/CNBC कॉल्स",
    "🎯 ब्रोकरेज टारगेट्स", 
    "🚀 मार्केट & सेक्टर पल्स", 
    "🐦 Twitter पल्स"
])

# ================= TAB 1: रिज़ल्ट्स वर्डिक्ट (Bullish vs Bearish) =================
with tab1:
    st.subheader("📊 कॉर्पोरेट नतीजे: बुलिश / बेयरिश वर्डिक्ट")
    st.caption("हाल ही में घोषित वित्तीय नतीजों का स्वचालित विश्लेषण:")
    
    if st.button("🔄 सभी कंपनियों के ताज़ा नतीजे व वर्डिक्ट लोड करें", use_container_width=True, key="btn_res_verdict"):
        with st.spinner("तिमाही वित्तीय नतीजों की जांच हो रही है..."):
            res_items = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=25)
            if res_items:
                for item in res_items:
                    verdict, desc = analyze_earnings_verdict(item["title"])
                    st.markdown(f"**[{verdict}]** `{item['stock']}` — *{desc}*")
                    st.markdown(f"[{item['title']}]({item['link']})")
                    st.caption(f"तारीख: {item['date']}")
                    st.divider()
            else:
                st.info("कोई हालिया कॉर्पोरेट रिजल्ट अपडेट नहीं मिला।")

    st.write("---")
    st.subheader("🔍 किसी खास शेयर का रिज़ल्ट चेक करें")
    target_res_stk = st.selectbox("स्टॉक चुनें:", ALL_FNO_STOCKS, key="box_res_stk")
    if st.button(f"{target_res_stk} के नतीजों का विश्लेषण देखें", use_container_width=True):
        single_res = fetch_stock_specific(target_res_stk, "results")
        if single_res:
            for sr in single_res:
                v, d = analyze_earnings_verdict(sr["title"])
                st.markdown(f"**[{v}]** [{sr['title']}]({sr['link']})")
                st.caption(f"अपडेट: {sr['date']}")
        else:
            st.info(f"{target_res_stk} पर कोई ताज़ा वित्तीय नतीजा नहीं मिला।")

# ================= TAB 2: हाई-इम्पैक्ट न्यूज़ =================
with tab2:
    st.subheader("⚡ हाई-इम्पैक्ट व महत्वपूर्ण खबरें")
    st.caption("सेबी नोटिस, बड़े ऑर्डर्स, यूएसएफडीए, मर्जर और पेनल्टी से जुड़ी बड़ी खबरें:")
    
    if st.button("🔄 सभी बड़ी मार्केट-मूविंग खबरें लोड करें", use_container_width=True, key="btn_impact_news"):
        with st.spinner("हाई-इम्पैक्ट खबरों को फ़िल्टर किया जा रहा है..."):
            news_items = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda+OR+acquisition+OR+resigns)+share+India", limit=25)
            if news_items:
                for n in news_items:
                    impact_tag, _ = analyze_news_impact(n["title"])
                    st.markdown(f"**[{impact_tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.caption(f"समय: {n['date']}")
                    st.divider()
            else:
                st.info("कोई हाई-इम्पैक्ट न्यूज़ नहीं मिली।")

    st.write("---")
    st.subheader("🔍 किसी खास शेयर की बड़ी खबर खोजें")
    target_n_stk = st.selectbox("स्टॉक चुनें:", ALL_FNO_STOCKS, key="box_news_stk")
    if st.button(f"{target_n_stk} की महत्वपूर्ण खबरें देखें", use_container_width=True):
        single_n = fetch_stock_specific(target_n_stk, "impact_news")
        if single_n:
            for sn in single_n:
                tag, _ = analyze_news_impact(sn["title"])
                st.markdown(f"**[{tag}]** [{sn['title']}]({sn['link']})")
                st.caption(f"तारीख: {sn['date']}")
        else:
            st.info(f"{target_n_stk} पर कोई विशिष्ट खबर नहीं मिली।")

# ================= TAB 3: Zee Business & CNBC Awaaz =================
with tab3:
    st.subheader("📺 आज के सभी टीवी चैनल कॉल्स (ऑटोमैटिक)")
    if st.button("🔄 सभी ताज़ा टीवी सिफारिशें लोड करें", use_container_width=True, key="btn_tv_auto"):
        with st.spinner("टीवी चैनल्स के ताज़ा कॉल्स स्कैन हो रहे हैं..."):
            auto_tv = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=20)
            if auto_tv:
                for item in auto_tv:
                    ch_tag = "🟢 Zee Business" if "zee" in item["title"].lower() else ("🔵 CNBC Awaaz" if "cnbc" in item["title"].lower() or "awaaz" in item["title"].lower() else "📺 Business TV")
                    st.markdown(f"**[{ch_tag}]** `{item['stock']}` | [{item['title']}]({item['link']})")
                    st.caption(f"समय: {item['date']}")
                    st.divider()
            else:
                st.info("कोई ताज़ा टीवी ब्रॉडकास्ट अपडेट नहीं मिला।")

    st.write("---")
    st.subheader("🔍 किसी शेयर की टीवी कॉल्स खोजें")
    single_tv_stock = st.selectbox("स्टॉक चुनें:", ALL_FNO_STOCKS, key="box_tv_single")
    if st.button(f"{single_tv_stock} की टीवी सिफारिशें देखें", use_container_width=True):
        res = fetch_stock_specific(single_tv_stock, "tv")
        if res:
            for r in res:
                st.markdown(f"• [{r['title']}]({r['link']})")
                st.caption(f"तारीख: {r['date']}")

# ================= TAB 4: ब्रोकरेज टारगेट्स =================
with tab4:
    st.subheader("🎯 आज की सभी ब्रोकरेज सिफारिशें व टारगेट्स")
    if st.button("🔄 सभी ताज़ा ब्रोकरेज टारगेट्स लोड करें", use_container_width=True, key="btn_brok_auto"):
        with st.spinner("ब्रोकरेज रिपोर्ट्स व टारगेट्स फ़िल्टर हो रहे हैं..."):
            auto_brok = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=20)
            if auto_brok:
                for b in auto_brok:
                    t_low = b["title"].lower()
                    call = "🟢 BUY / TARGET UP" if any(w in t_low for w in ["buy", "raised", "upgrade", "bullish"]) else ("🔴 SELL / TARGET CUT" if any(w in t_low for w in ["sell", "cut", "downgrade", "bearish"]) else "⚪ TARGET UPDATE")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.caption(f"समय: {b['date']}")
                    st.divider()
            else:
                st.info("कोई ताज़ा ब्रोकरेज रिपोर्ट नहीं मिली।")

    st.write("---")
    st.subheader("🔍 किसी खास शेयर का ब्रोकरेज टारगेट खोजें")
    single_brok_stock = st.selectbox("स्टॉक चुनें:", ALL_FNO_STOCKS, key="box_brok_single")
    if st.button(f"{single_brok_stock} के ब्रोकरेज टारगेट्स देखें", use_container_width=True):
        res = fetch_stock_specific(single_brok_stock, "brokerage")
        if res:
            for r in res:
                st.markdown(f"• [{r['title']}]({r['link']})")
                st.caption(f"तारीख: {r['date']}")

# ================= TAB 5: सेक्टोरल & मार्केट पल्स =================
with tab5:
    st.subheader("🌐 इंडेक्स, सेक्टर और टॉप स्टॉक्स स्कैनर")
    if st.button("📊 पूरा मार्केट सेंटिमेंट स्कैन करें", use_container_width=True, key="btn_mkt_scan"):
        with st.spinner("इंडेक्स और 35 प्रमुख F&O स्टॉक्स स्कैन हो रहे हैं..."):
            all_data = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = executor.map(lambda s: fetch_stock_specific(s, "general"), ALL_FNO_STOCKS[:35])
                for r_list in results:
                    all_data.extend(r_list)

            if all_data:
                df = pd.DataFrame(all_data)
                df["sector"] = df["stock"].map(STOCK_SECTOR_MAP).fillna("Other")
                
                # पॉजिटिव / नेगेटिव स्कोर
                def quick_score(t):
                    tl = t.lower()
                    if any(w in tl for w in ["surge", "gain", "profit", "jump", "rally", "buy", "up"]): return 1
                    if any(w in tl for w in ["fall", "crash", "loss", "drop", "down", "sell"]): return -1
                    return 0
                df["score"] = df["title"].apply(quick_score)

                sec_df = df.groupby("sector")["score"].sum().reset_index().sort_values(by="score", ascending=False)
                sec_df["ट्रेंड"] = sec_df["score"].apply(lambda s: "🟢 मजबूत" if s > 0 else ("🔴 कमजोर" if s < 0 else "⚪ न्यूट्रल"))
                
                st.write("### 🏢 सेक्टर्स की स्थिति")
                st.dataframe(sec_df.rename(columns={"sector": "सेक्टर", "score": "सेंटीमेंट स्कोर"}), use_container_width=True, hide_index=True)

                st.divider()
                stk_df = df.groupby(["stock", "sector"])["score"].sum().reset_index().sort_values(by="score", ascending=False)
                c1, c2 = st.columns(2)
                with c1:
                    st.success("🟢 **टॉप बुलिश स्टॉक्स**")
                    st.dataframe(stk_df[stk_df["score"] > 0].head(8).rename(columns={"stock": "शेयर", "sector": "सेक्टर", "score": "स्कोर"}), use_container_width=True, hide_index=True)
                with c2:
                    st.error("🔴 **टॉप बेयरिश स्टॉक्स**")
                    st.dataframe(stk_df[stk_df["score"] < 0].tail(8).rename(columns={"stock": "शेयर", "sector": "सेक्टर", "score": "स्कोर"}), use_container_width=True, hide_index=True)

# ================= TAB 6: Twitter पल्स =================
with tab6:
    st.subheader("🐦 सोशल मीडिया ब्रेकआउट व ट्रेंड्स (ऑटो)")
    if st.button("🔄 सभी ताज़ा सोशल चर्चाएँ लोड करें", use_container_width=True, key="btn_tw_auto"):
        with st.spinner("Twitter ट्रेंड्स स्कैन हो रहे हैं..."):
            auto_tw = fetch_rss_feed("stock+breakout+OR+multibagger+twitter+India", limit=15)
            if auto_tw:
                for tw in auto_tw:
                    st.markdown(f"• `{tw['stock']}` | [{tw['title']}]({tw['link']})")
                    st.divider()
            else:
                st.info("कोई ताज़ा ट्रेंड नहीं मिला।")
