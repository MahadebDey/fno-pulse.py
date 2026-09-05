import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# ================= 1. पेज कॉन्फ़िगरेशन व स्टाइल =================
st.set_page_config(
    page_title="महादेब स्टॉक रिसर्च",
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

st.title("⚡ महादेब स्टॉक रिसर्च")
st.caption("F&O मार्केट इंटेलिजेंस: इंडेक्स व सेक्टर ट्रेंड्स, टॉप बुलिश/बेयरिश शेयर, VWAP, रिजल्ट्स व टीवी सिफारिशें")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 2. सभी इंडेक्स व सेक्टर्स =================
ALL_SECTOR_INDICES = {
    "निफ्टी 50 (Nifty 50)": "^NSEI",
    "बैंक निफ्टी (Bank Nifty)": "^NSEBANK",
    "निफ्टी आईटी (IT)": "^CNXIT",
    "निफ्टी ऑटो (Auto)": "^CNXAUTO",
    "निफ्टी मेटल (Metal)": "^CNXMETAL",
    "निफ्टी एफएमसीजी (FMCG)": "^CNXFMCG",
    "निफ्टी फार्मा (Pharma)": "^CNXPHARMA",
    "निफ्टी फिन सर्विसेज (Fin Services)": "NIFTY_FIN_SERVICE.NS",
    "निफ्टी एनर्जी (Energy)": "^CNXENERGY",
    "निफ्टी रियल्टी (Realty)": "^CNXREALTY",
    "निफ्टी पीएसयू बैंक (PSU Bank)": "^CNXPSUBANK",
    "निफ्टी मीडिया (Media)": "^CNXMEDIA",
    "निफ्टी इंफ्रा (Infra)": "^CNXINFRA"
}

STOCK_SECTOR_MAP = {
    # बैंकिंग व वित्तीय सेवाएं
    "HDFCBANK": "बैंकिंग", "ICICIBANK": "बैंकिंग", "SBIN": "बैंकिंग", "AXISBANK": "बैंकिंग",
    "KOTAKBANK": "बैंकिंग", "INDUSINDBK": "बैंकिंग", "BANKBARODA": "बैंकिंग", "PNB": "बैंकिंग",
    "BAJFINANCE": "फाइनेंशियल", "BAJAJFINSV": "फाइनेंशियल", "CHOLAFIN": "फाइनेंशियल", "MUTHOOTFIN": "फाइनेंशियल",
    "PFC": "फाइनेंशियल", "RECLTD": "फाइनेंशियल", "SHRIRAMFIN": "फाइनेंशियल", "MOTILALOFS": "फाइनेंशियल",
    
    # आईटी व टेक
    "TCS": "आईटी", "INFY": "आईटी", "HCLTECH": "आईटी", "WIPRO": "आईटी", "TECHM": "आईटी", 
    "LTIM": "आईटी", "COFORGE": "आईटी", "PERSISTENT": "आईटी", "MPHASIS": "आईटी", "NAUKRI": "आईटी",
    
    # ऑटोमोबाइल
    "TATAMOTORS": "ऑटो", "MARUTI": "ऑटो", "M&M": "ऑटो", "BAJAJ-AUTO": "ऑटो", 
    "HEROMOTOCO": "ऑटो", "EICHERMOT": "ऑटो", "TVSMOTOR": "ऑटो", "BHARATFORG": "ऑटो", 
    "APOLLOTYRE": "ऑटो", "BALKRISIND": "ऑटो", "MOTHERSON": "ऑटो",
    
    # मेटल व माइनिंग
    "TATASTEEL": "मेटल", "JSWSTEEL": "मेटल", "HINDALCO": "मेटल", "JINDALSTEL": "मेटल", 
    "VEDL": "मेटल", "COALINDIA": "मेटल", "NMDC": "मेटल", "NATIONALUM": "मेटल", "SAIL": "मेटल",
    
    # एनर्जी, ऑइल व पावर
    "RELIANCE": "एनर्जी/ऑइल", "BPCL": "एनर्जी/ऑइल", "IOC": "एनर्जी/ऑइल", "ONGC": "एनर्जी/ऑइल", 
    "NTPC": "पावर", "POWERGRID": "पावर", "TATAPOWER": "पावर", "ADANIENT": "एनर्जी", "ADANIPORTS": "इंफ्रा",
    
    # फार्मा व हेल्थकेयर
    "SUNPHARMA": "फार्मा", "CIPLA": "फार्मा", "DRREDDY": "फार्मा", "DIVISLAB": "फार्मा", 
    "LUPIN": "फार्मा", "AUROPHARMA": "फार्मा", "APOLLOHOSP": "फार्मा", "ZYDUSLIFE": "फार्मा",
    
    # एफएमसीजी व उपभोग
    "ITC": "एफएमसीजी", "HINDUNILVR": "एफएमसीजी", "NESTLEIND": "एफएमसीजी", "BRITANNIA": "एफएमसीजी", 
    "DABUR": "एफएमसीजी", "TATACONSUM": "एफएमसीजी", "TITAN": "कंज्यूमर", "ASIANPAINT": "कंज्यूमर",
    
    # इंफ्रा व केबल्स
    "LT": "इंफ्रा", "ULTRACEMCO": "सीमेंट", "GRASIM": "सीमेंट", "AMBUJACEM": "सीमेंट", 
    "POLYCAB": "केबल्स", "HAVELLS": "कंज्यूमर इलेक्ट्रॉनिक्स", "DIXON": "इलेक्ट्रॉनिक्स", "DLF": "रियल्टी"
}

ALL_FNO_STOCKS = sorted(list(STOCK_SECTOR_MAP.keys()))

# ================= 3. सहायक फंक्शंस =================
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
                matched = "मार्केट"
                for stk in ALL_FNO_STOCKS:
                    if stk.lower() in title.lower():
                        matched = stk
                        break
                results.append({"stock": matched, "title": title, "link": link, "date": date})
    except Exception:
        pass
    return results

# ================= 4. इंडेक्स व सेक्टर स्कैनर =================
def scan_sector_item(item):
    name, ticker = item
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if len(data) < 5:
            return None

        cmp_val = round(float(data['Close'].iloc[-1]), 2)
        prev_close = round(float(data['Close'].iloc[-2]), 2)
        chg_pct = round(((cmp_val - prev_close) / prev_close) * 100, 2)
        ema20 = round(float(data['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)
        pdh = round(float(data['High'].iloc[-2]), 2)
        pdl = round(float(data['Low'].iloc[-2]), 2)

        score = 0
        if chg_pct > 0: score += 1
        if cmp_val > ema20: score += 1
        if cmp_val > pdh: score += 1
        if chg_pct < 0: score -= 1
        if cmp_val < ema20: score -= 1
        if cmp_val < pdl: score -= 1

        if score >= 2: status = "🟢 मजबूत तेजी (Super Bullish)"
        elif score == 1: status = "🟢 हल्की तेजी (Mild Bullish)"
        elif score <= -2: status = "🔴 भारी मंदी (Super Bearish)"
        elif score == -1: status = "🔴 हल्की मंदी (Mild Bearish)"
        else: status = "⚪ साइडवेज़ / न्यूट्रल"

        return {
            "इंडेक्स / सेक्टर": name,
            "मौजूदा भाव (CMP)": cmp_val,
            "बदलाव (%)": f"{'+' if chg_pct > 0 else ''}{chg_pct}%",
            "ट्रेंड स्थिति": status,
            "20 EMA संकेत": "20 EMA के ऊपर" if cmp_val >= ema20 else "20 EMA के नीचे",
            "PDH/PDL ब्रेकआउट": "कल का हाई तोड़ा (PDH Cross)" if cmp_val > pdh else ("कल का लो तोड़ा (PDL Break)" if cmp_val < pdl else "दायरे में (In Range)")
        }
    except Exception:
        return None

# ================= 5. मल्टी-फैक्टर स्टॉक विश्लेषक =================
def analyze_stock_full(symbol):
    ticker = f"{symbol}.NS"
    score = 0.0
    details = {
        "शेयर": symbol,
        "सेक्टर": STOCK_SECTOR_MAP.get(symbol, "अन्य"),
        "भाव (₹)": 0.0,
        "तकनीकी रुझान": "⚪ न्यूट्रल",
        "ट्विटर पल्स": "⚪ सामान्य",
        "रिजल्ट/खबरें": "⚪ सामान्य",
        "कुल स्कोर": 0.0
    }
    
    try:
        daily = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.get_level_values(0)
            
        if len(daily) >= 25:
            cmp_val = round(float(daily['Close'].iloc[-1]), 2)
            pdh = round(float(daily['High'].iloc[-2]), 2)
            pdl = round(float(daily['Low'].iloc[-2]), 2)
            ema20 = round(float(daily['Close'].ewm(span=20, adjust=False).mean().iloc[-1]), 2)
            details["भाव (₹)"] = cmp_val

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
            details["तकनीकी रुझान"] = "🟢 मजबूत" if tech_points > 1.5 else ("🔴 कमजोर" if tech_points < -1.5 else "⚪ न्यूट्रल")

        # ट्विटर सेंटिमेंट
        tw_feed = fetch_rss_feed(f"{symbol}+stock+twitter+OR+{symbol}+breakout", limit=3)
        tw_sc = 0
        for tw in tw_feed:
            tw_sc += quick_text_score(tw['title'], ["surge", "breakout", "buy", "bullish", "rally"], ["fall", "crash", "bearish", "loss", "drop"])
        
        if tw_sc > 0:
            score += 1.5
            details["ट्विटर पल्स"] = "🟢 बुलिश बज"
        elif tw_sc < 0:
            score -= 1.5
            details["ट्विटर पल्स"] = "🔴 बेयरिश बज"

        # नतीजे व खबरें
        news_feed = fetch_rss_feed(f"{symbol}+share+(results+OR+profit+OR+order+OR+sebi+OR+target)", limit=3)
        n_sc = 0
        for nf in news_feed:
            n_sc += quick_text_score(nf['title'], 
                                     ["profit jumps", "pat rises", "beats estimates", "bags order", "target raised", "upgrade"], 
                                     ["profit falls", "pat drops", "misses estimates", "penalty", "sebi", "downgrade", "cut"])
        
        if n_sc > 0:
            score += 2.0
            details["रिजल्ट/खबरें"] = "🟢 सकारात्मक खबर"
        elif n_sc < 0:
            score -= 2.0
            details["रिजल्ट/खबरें"] = "🔴 नकारात्मक खबर"

        details["कुल स्कोर"] = round(score, 2)
        return details
    except Exception:
        return None

# ================= 6. ऊपर-से-नीचे सीरियल इंटरफ़ेस =================

# सेक्शन 1: सभी इंडेक्स व सेक्टर्स का ट्रेंड
with st.expander("🏛️ भाग 1: सभी सेक्टर्स व इंडेक्स का लाइव ट्रेंड (तेजी vs मंदी)", expanded=True):
    st.write("**निफ्टी 50, बैंक निफ्टी, आईटी, ऑटो, मेटल, फार्मा, रियल्टी, पीएसयू बैंक आदि का लाइव स्टेटस:**")
    
    if st.button("📊 सभी इंडेक्स व सेक्टर्स स्कैन करें", use_container_width=True, key="btn_scan_sectors"):
        with st.spinner("सभी 13 सेक्टर्स और इंडेक्स का लाइव ट्रेंड लोड हो रहा है..."):
            sec_results = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                res = executor.map(scan_sector_item, ALL_SECTOR_INDICES.items())
                for r in res:
                    if r: sec_results.append(r)
            
            if sec_results:
                sdf = pd.DataFrame(sec_results)
                bull_sec = sdf[sdf['ट्रेंड स्थिति'].str.contains("Bullish|तेजी", na=False)]
                bear_sec = sdf[sdf['ट्रेंड स्थिति'].str.contains("Bearish|मंदी", na=False)]

                col1, col2 = st.columns(2)
                with col1:
                    st.success(f"🟢 **तेज / मजबूत सेक्टर्स ({len(bull_sec)})**")
                    if not bull_sec.empty:
                        st.dataframe(bull_sec[["इंडेक्स / सेक्टर", "मौजूदा भाव (CMP)", "बदलाव (%)", "ट्रेंड स्थिति"]], use_container_width=True, hide_index=True)
                    else:
                        st.write("अभी कोई सेक्टर मजबूत तेजी में नहीं है।")
                with col2:
                    st.error(f"🔴 **मंदे / कमजोर सेक्टर्स ({len(bear_sec)})**")
                    if not bear_sec.empty:
                        st.dataframe(bear_sec[["इंडेक्स / सेक्टर", "मौजूदा भाव (CMP)", "बदलाव (%)", "ट्रेंड स्थिति"]], use_container_width=True, hide_index=True)
                    else:
                        st.write("अभी कोई सेक्टर मंदी में नहीं है।")

                st.write("---")
                st.write("### 📋 पूरी सेक्टोरल हीटमैप टेबल")
                st.dataframe(sdf, use_container_width=True, hide_index=True)
            else:
                st.warning("इंडेक्स डेटा लोड नहीं हो सका। कृपया पुनः प्रयास करें।")

# सेक्शन 2: मल्टी-फैक्टर टॉप 5 बुलिश और बेयरिश शेयर
with st.expander("⭐ भाग 2: टॉप 5 बुलिश और बेयरिश शेयर (मल्टी-फैक्टर विश्लेषण)", expanded=True):
    st.write("**तकनीकी आंकड़े (VWAP, PDH/PDL, 20 EMA) + ट्विटर पल्स + तिमाही नतीजे + खबरों के आधार पर चयनित टॉप 5 शेयर:**")
    
    scan_limit = st.slider("स्कैन करने के लिए लिक्विड शेयरों की संख्या चुनें:", min_value=15, max_value=len(ALL_FNO_STOCKS), value=25, step=5)
    
    if st.button("🔥 मल्टी-फैक्टर मार्केट विश्लेषण शुरू करें", use_container_width=True, key="btn_deep_analysis"):
        with st.spinner(f"{scan_limit} शेयरों का VWAP, ट्विटर बज, तिमाही नतीजे व खबरें स्कैन हो रही हैं..."):
            stock_sublist = ALL_FNO_STOCKS[:scan_limit]
            analysis_data = []
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                items = executor.map(analyze_stock_full, stock_sublist)
                for itm in items:
                    if itm and itm["भाव (₹)"] > 0:
                        analysis_data.append(itm)
            
            if analysis_data:
                mdf = pd.DataFrame(analysis_data)
                sorted_df = mdf.sort_values(by="कुल स्कोर", ascending=False)
                top_bulls = sorted_df.head(5)
                top_bears = sorted_df.tail(5).iloc[::-1]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.success("🟢 **शीर्ष 5 बुलिश शेयर (तेजी के लिए अनुकूल)**")
                    st.dataframe(
                        top_bulls[["शेयर", "सेक्टर", "भाव (₹)", "तकनीकी रुझान", "ट्विटर पल्स", "रिजल्ट/खबरें", "कुल स्कोर"]], 
                        use_container_width=True, 
                        hide_index=True
                    )
                with col_b:
                    st.error("🔴 **शीर्ष 5 बेयरिश शेयर (मंदी के शिकार)**")
                    st.dataframe(
                        top_bears[["शेयर", "सेक्टर", "भाव (₹)", "तकनीकी रुझान", "ट्विटर पल्स", "रिजल्ट/खबरें", "कुल स्कोर"]], 
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                st.divider()
                st.write("### 📋 स्कैन किए गए सभी शेयरों की रैंकिंग सूची")
                st.dataframe(sorted_df, use_container_width=True, hide_index=True)
            else:
                st.warning("डेटा फेच नहीं हो पाया। कृपया दोबारा बटन दबाएं।")

# सेक्शन 3: टेक्निकल व इंट्राडे VWAP रडार
with st.expander("🎯 भाग 3: टेक्निकल व इंट्राडे VWAP रडार", expanded=False):
    st.write("**लाइव VWAP, कल का हाई/लो ब्रेकआउट और 20 EMA ट्रेंड स्थिति:**")
    if st.button("🚀 लाइव टेक्निकल स्कैन चलाएं", use_container_width=True, key="btn_tech_only"):
        with st.spinner("VWAP और कैंडल डेटा प्रोसेस हो रहा है..."):
            t_data = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                res = executor.map(analyze_stock_full, ALL_FNO_STOCKS[:20])
                for r in res:
                    if r and r["भाव (₹)"] > 0: t_data.append(r)
            if t_data:
                tdf = pd.DataFrame(t_data)
                st.dataframe(tdf[["शेयर", "सेक्टर", "भाव (₹)", "तकनीकी रुझान", "कुल स्कोर"]], use_container_width=True, hide_index=True)

# सेक्शन 4: तिमाही कॉर्पोरेट नतीजे व वर्डिक्ट
with st.expander("📊 भाग 4: कॉर्पोरेट रिजल्ट्स व अर्निंग्स वर्डिक्ट", expanded=False):
    st.write("**तिमाही नतीजे (Q1/Q2/Q3/Q4): शुद्ध मुनाफा, PAT और अनुमानों पर खरा उतरा या नहीं:**")
    if st.button("🔄 ताज़ा तिमाही नतीजे लोड करें", use_container_width=True, key="btn_res"):
        with st.spinner("वित्तीय नतीजों की समीक्षा हो रही है..."):
            res_list = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=15)
            if res_list:
                for r in res_list:
                    t = r['title'].lower()
                    is_bull = any(k in t for k in ["profit jumps", "pat rises", "net profit up", "beats estimates", "revenue up"])
                    is_bear = any(k in t for k in ["profit falls", "pat drops", "net loss", "misses estimates", "revenue declines"])
                    v_badge = "🟢 बुलिश नतीजा (शानदार)" if is_bull else ("🔴 बेयरिश नतीजा (कमजोर)" if is_bear else "⚪ सामान्य घोषणा")
                    st.markdown(f"**[{v_badge}]** `{r['stock']}` | [{r['title']}]({r['link']})")
                    st.caption(f"प्रकाशित समय: {r['date']}")
                    st.divider()

# सेक्शन 5: हाई-इम्पैक्ट बड़ी खबरें
with st.expander("⚡ भाग 5: बाज़ार हिलाने वाली बड़ी खबरें (High-Impact)", expanded=False):
    st.write("**सेबी नोटिस, बड़े ऑर्डर्स, पेनल्टी, यूएसएफडीए और मैनेजमेंट से जुड़ी अहम खबरें:**")
    if st.button("🔄 सभी बड़ी मार्केट-मूविंग खबरें लोड करें", use_container_width=True, key="btn_impact"):
        with st.spinner("बड़ी खबरों को छांटा जा रहा है..."):
            news_list = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda+OR+acquisition)+share+India", limit=15)
            if news_list:
                for n in news_list:
                    tl = n['title'].lower()
                    tag = "🟢 सकारात्मक खबर (पॉजिटिव)" if any(k in tl for k in ["bags order", "wins contract", "approval", "acquires", "upgrade"]) else ("🔴 नकारात्मक खबर (निगेटिव)" if any(k in tl for k in ["penalty", "probe", "raid", "sebi", "usfda"]) else "⚪ सामान्य समाचार")
                    st.markdown(f"**[{tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.caption(f"समय: {n['date']}")
                    st.divider()

# सेक्शन 6: ज़ी बिज़नेस व सीएनबीसी आवाज़ रिसर्च
with st.expander("📺 भाग 6: ज़ी बिज़नेस व सीएनबीसी आवाज़ की सिफारिशें", expanded=False):
    st.write("**टीवी चैनल पैनलिस्ट, अनिल सिंघवी की राय और ट्रेडिंग कॉल्स:**")
    if st.button("🔄 टीवी रिसर्च कॉल्स लोड करें", use_container_width=True, key="btn_tv"):
        with st.spinner("टीवी चैनल्स के रिसर्च कॉल्स फेच हो रहे हैं..."):
            tv_list = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=15)
            if tv_list:
                for t in tv_list:
                    src = "🟢 ज़ी बिज़नेस (Zee Business)" if "zee" in t['title'].lower() else ("🔵 सीएनबीसी आवाज़ (CNBC Awaaz)" if "cnbc" in t['title'].lower() else "📺 बिज़नेस टीवी")
                    st.markdown(f"**[{src}]** `{t['stock']}` | [{t['title']}]({t['link']})")
                    st.caption(f"प्रसारण समय: {t['date']}")
                    st.divider()

# सेक्शन 7: ब्रोकरेज हाउसेस के टारगेट्स
with st.expander("🎯 भाग 7: बड़े ब्रोकरेज हाउसेस के टारगेट प्राइस", expanded=False):
    st.write("**Morgan Stanley, Jefferies, CLSA, Motilal Oswal आदि के टारगेट और रेटिंग्स:**")
    if st.button("🔄 ब्रोकरेज टारगेट्स लोड करें", use_container_width=True, key="btn_brok"):
        with st.spinner("ब्रोकरेज रिपोर्ट्स फेच की जा रही हैं..."):
            brok_list = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=15)
            if brok_list:
                for b in brok_list:
                    tl = b['title'].lower()
                    call = "🟢 खरीदारी / टारगेट बढ़ाया" if any(w in tl for w in ["buy", "raised", "upgrade"]) else ("🔴 बिकवाली / टारगेट घटाया" if any(w in tl for w in ["sell", "cut", "downgrade"]) else "⚪ टारगेट अपडेट")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.caption(f"जारी तिथि: {b['date']}")
                    st.divider()

# सेक्शन 8: किसी एक शेयर की पूरी जानकारी (Deep-Dive)
with st.expander("🔍 भाग 8: किसी खास शेयर का पूरा विश्लेषण (Search)", expanded=False):
    target_symbol = st.selectbox("F&O शेयर चुनें जिसका पूरा डेटा देखना चाहते हैं:", ALL_FNO_STOCKS)
    if st.button(f"{target_symbol} का मुकम्मल कच्चा-चिट्ठा निकालें", use_container_width=True):
        with st.spinner(f"{target_symbol} का पूरा डेटा तैयार हो रहा है..."):
            full_stat = analyze_stock_full(target_symbol)
            if full_stat:
                st.write("#### 📊 संपूर्ण स्कोर कार्ड")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("मौजूदा भाव (CMP)", f"₹{full_stat['भाव (₹)']}")
                c2.metric("तकनीकी रुझान", full_stat["तकनीकी रुझान"])
                c3.metric("ट्विटर पल्स", full_stat["ट्विटर पल्स"])
                c4.metric("कुल स्कोर", full_stat["कुल स्कोर"])
                st.caption(f"सेक्टर: {full_stat['सेक्टर']} | नतीजे व खबरें: {full_stat['रिजल्ट/खबरें']}")
            
            st.write("#### 📰 हालिया सुर्खियां व मीडिया")
            custom_feed = fetch_rss_feed(f"{target_symbol}+share+India", limit=5)
            if custom_feed:
                for item in custom_feed:
                    st.markdown(f"• [{item['title']}]({item['link']})")
                    st.caption(f"समय: {item['date']}")
