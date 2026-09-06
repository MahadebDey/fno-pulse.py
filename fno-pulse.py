import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# DhanHQ Integration
try:
    from dhanhq import dhanhq
    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False

# ================= 1. Page Configuration & Custom CSS =================
st.set_page_config(
    page_title="महादेब स्टॉक रिसर्च",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
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

# ================= 2. Master Password Security Guard =================
MASTER_PIN = "990553"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 महादेब स्टॉक रिसर्च")
    st.subheader("सुरक्षित ट्रेडिंग गेटवे")
    st.info("यह एक निजी रिसर्च व ट्रेडिंग पोर्टल है। कृपया एक्सेस के लिए अपना मास्टर पिन दर्ज करें।")
    
    with st.form("login_form"):
        pin_input = st.text_input("मास्टर पिन दर्ज करें:", type="password", placeholder="******")
        submit_btn = st.form_submit_button("लॉगिन करें", use_container_width=True)
        
        if submit_btn:
            if str(pin_input).strip() == MASTER_PIN:
                st.session_state.authenticated = True
                st.success("सत्यापन सफल! डैशबोर्ड लोड हो रहा है...")
                st.rerun()
            else:
                st.error("गलत पिन! कृपया पुनः प्रयास करें।")
    st.stop()

# ================= 3. Dhan API Connection (Sidebar) =================
with st.sidebar:
    st.header("⚡ Dhan API Setup")
    st.caption("Enter your 24-hour Dhan access token:")
    dhan_client_id = st.text_input("Dhan Client ID", value=st.session_state.get("dhan_client_id", ""), type="password")
    dhan_token = st.text_input("Dhan Access Token", value=st.session_state.get("dhan_token", ""), type="password")
    
    dhan_instance = None
    if dhan_client_id and dhan_token and DHAN_AVAILABLE:
        clean_id = str(dhan_client_id).strip()
        clean_tok = str(dhan_token).strip()
        try:
            # Multi-version compatibility handling for dhanhq
            try:
                temp_dhan = dhanhq(client_id=clean_id, access_token=clean_tok)
            except TypeError:
                try:
                    temp_dhan = dhanhq(clean_tok)
                except TypeError:
                    temp_dhan = dhanhq(clean_id, clean_tok)

            test_resp = temp_dhan.get_fund_limits()
            if test_resp and test_resp.get("status") == "success":
                dhan_instance = temp_dhan
                st.session_state["dhan_client_id"] = clean_id
                st.session_state["dhan_token"] = clean_tok
                st.success("🟢 Dhan API Live Connected")
            else:
                remarks = test_resp.get("remarks") if test_resp else "Token Validation Failed"
                st.error(f"Dhan Error: {remarks}")
                dhan_instance = None
        except Exception as e:
            st.error(f"Connection Exception: {str(e)}")
            dhan_instance = None
    else:
        st.info("⚪ Yahoo Finance Backup Active")

    st.divider()
    st.subheader("🛡️ Risk & Kill Switch")
    max_daily_loss = st.number_input("Max Daily Loss Limit (₹):", min_value=500.0, value=3000.0, step=500.0)
    st.caption(f"Positions will auto-square off if MTM loss hits -₹{max_daily_loss}")

    st.divider()
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("⚡ महादेब स्टॉक रिसर्च")
st.caption("F&O मार्केट इंटेलिजेंस + DhanHQ Advanced Options Trading Terminal")

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= 4. Stock & Security Mapping =================
DHAN_SEC_IDS = {
    "NIFTY": "13",
    "BANKNIFTY": "25",
    "HDFCBANK": "1333", 
    "ICICIBANK": "4963", 
    "SBIN": "3045", 
    "AXISBANK": "5900",
    "KOTAKBANK": "1922", 
    "TCS": "11536", 
    "INFY": "1594", 
    "TATAMOTORS": "3456",
    "RELIANCE": "2885", 
    "TATASTEEL": "3499", 
    "MARUTI": "10999", 
    "BAJFINANCE": "317"
}

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
    "HDFCBANK": "बैंकिंग", "ICICIBANK": "बैंकिंग", "SBIN": "बैंकिंग", "AXISBANK": "बैंकिंग",
    "KOTAKBANK": "बैंकिंग", "INDUSINDBK": "बैंकिंग", "BANKBARODA": "बैंकिंग", "PNB": "बैंकिंग",
    "BAJFINANCE": "फाइनेंशियल", "BAJAJFINSV": "फाइनेंशियल", "CHOLAFIN": "फाइनेंशियल", "MUTHOOTFIN": "फाइनेंशियल",
    "PFC": "फाइनेंशियल", "RECLTD": "फाइनेंशियल", "SHRIRAMFIN": "फाइनेंशियल", "MOTILALOFS": "फाइनेंशियल",
    "TCS": "आईटी", "INFY": "आईटी", "HCLTECH": "आईटी", "WIPRO": "आईटी", "TECHM": "आईटी", 
    "LTIM": "आईटी", "COFORGE": "आईटी", "PERSISTENT": "आईटी", "MPHASIS": "आईटी", "NAUKRI": "आईटी",
    "TATAMOTORS": "ऑटो", "MARUTI": "ऑटो", "M&M": "ऑटो", "BAJAJ-AUTO": "ऑटो", 
    "HEROMOTOCO": "ऑटो", "EICHERMOT": "ऑटो", "TVSMOTOR": "ऑटो", "BHARATFORG": "ऑटो", 
    "TATASTEEL": "मेटल", "JSWSTEEL": "मेटल", "HINDALCO": "मेटल", "JINDALSTEL": "मेटल", 
    "VEDL": "मेटल", "COALINDIA": "मेटल", "NMDC": "मेटल", "SAIL": "मेटल",
    "RELIANCE": "एनर्जी/ऑइल", "BPCL": "एनर्जी/ऑइल", "IOC": "एनर्जी/ऑइल", "ONGC": "एनर्जी/ऑइल", 
    "NTPC": "पावर", "POWERGRID": "पावर", "TATAPOWER": "पावर", "ADANIENT": "एनर्जी",
    "SUNPHARMA": "फार्मा", "CIPLA": "फार्मा", "DRREDDY": "फार्मा", "DIVISLAB": "फार्मा",
    "ITC": "एफएमसीजी", "HINDUNILVR": "एफएमसीजी", "NESTLEIND": "एफएमसीजी", "BRITANNIA": "एफएमसीजी",
    "LT": "इंफ्रा", "ULTRACEMCO": "सीमेंट", "GRASIM": "सीमेंट", "POLYCAB": "केबल्स"
}

ALL_FNO_STOCKS = sorted(list(STOCK_SECTOR_MAP.keys()))

# ================= 5. Data Feeds & Scanners =================
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

def scan_sector_item(item):
    name, ticker = item
    try:
        data = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if len(data) < 5: return None
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
        else: status = "⚪ साइडवेज़"

        return {
            "इंडेक्स / सेक्टर": name, "मौजूदा भाव (CMP)": cmp_val, "बदलाव (%)": f"{'+' if chg_pct > 0 else ''}{chg_pct}%",
            "ट्रेंड स्थिति": status, "20 EMA संकेत": "20 EMA के ऊपर" if cmp_val >= ema20 else "20 EMA के नीचे"
        }
    except Exception:
        return None

def analyze_stock_full(symbol):
    ticker = f"{symbol}.NS"
    score = 0.0
    details = {
        "शेयर": symbol, "सेक्टर": STOCK_SECTOR_MAP.get(symbol, "अन्य"), "भाव (₹)": 0.0,
        "तकनीकी रुझान": "⚪ न्यूट्रल", "ट्विटर पल्स": "⚪ सामान्य", "रिजल्ट/खबरें": "⚪ सामान्य", "कुल स्कोर": 0.0
    }
    try:
        cmp_val = 0.0
        if dhan_instance and symbol in DHAN_SEC_IDS:
            try:
                ltp_res = dhan_instance.get_quote(security_id=DHAN_SEC_IDS[symbol], exchange_segment="NSE_EQ")
                if ltp_res and ltp_res.get("status") == "success":
                    cmp_val = round(float(ltp_res['data'].get('last_price', 0)), 2)
            except Exception:
                pass

        daily = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if isinstance(daily.columns, pd.MultiIndex):
            daily.columns = daily.columns.get_level_values(0)
            
        if len(daily) >= 25:
            if cmp_val == 0.0:
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

        details["कुल स्कोर"] = round(score, 2)
        return details
    except Exception:
        return None

# ================= 6. ADVANCED TRADING TERMINAL =================
with st.expander("⚡ DHAN ADVANCED OPTIONS & EQUITY TRADING TERMINAL", expanded=True):
    if not dhan_instance:
        st.warning("⚠️ Dhan API Not Connected! Enter Client ID & Access Token in the sidebar to activate live execution.")
    else:
        total_pnl = 0.0
        try:
            p_check = dhan_instance.get_positions()
            if p_check and p_check.get("status") == "success" and p_check.get("data"):
                total_pnl = sum(float(p.get("unrealizedProfit", 0.0)) for p in p_check["data"] if p.get("netQty") != 0)
        except Exception:
            pass

        # Kill Switch Trigger
        if total_pnl <= -abs(max_daily_loss):
            st.error(f"🚨 KILL SWITCH ACTIVATED! Daily Loss (-₹{abs(total_pnl):.2f}) breached maximum threshold (-₹{max_daily_loss}).")
            if st.button("🚨 EMERGENCY SQUARE OFF ALL POSITIONS", type="primary", use_container_width=True):
                for p in p_check["data"]:
                    if p.get("netQty") != 0:
                        exit_side = dhan_instance.SELL if p.get("netQty") > 0 else dhan_instance.BUY
                        dhan_instance.place_order(
                            security_id=str(p.get("securityId")),
                            exchange_segment=dhan_instance.NSE_FNO if "OPT" in p.get("tradingSymbol", "") else dhan_instance.NSE,
                            transaction_type=exit_side,
                            quantity=abs(int(p.get("netQty"))),
                            order_type=dhan_instance.MARKET,
                            product_type=dhan_instance.INTRA,
                            price=0
                        )
                st.success("All active positions successfully terminated.")
                st.rerun()

        st.subheader("Order Placement & Position Management")
        tab_order, tab_pos, tab_pending = st.tabs(["🛒 Place Limit / SL Order", "📋 Open Positions (Live P&L)", "⏳ Pending Orders"])

        # TAB 1: Order Placement
        with tab_order:
            row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
            with row1_col1:
                symbol = st.selectbox("Underlying Asset", list(DHAN_SEC_IDS.keys()))
            with row1_col2:
                exchange_seg = st.selectbox("Exchange Segment", ["NSE_FNO (Options/Futures)", "NSE_EQ (Equity Cash)"])
            with row1_col3:
                order_side = st.radio("Side", ["BUY", "SELL"], horizontal=True)
            with row1_col4:
                product_type = st.selectbox("Product Type", ["INTRADAY (MIS)", "NORMAL (NRML/CNC)"])

            row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
            with row2_col1:
                quantity = st.number_input("Quantity (Lots / Shares)", min_value=1, value=25, step=1)
            with row2_col2:
                order_type = st.selectbox("Order Type", ["LIMIT", "MARKET"])
            with row2_col3:
                limit_price = st.number_input("Entry Limit Price (₹)", min_value=0.0, value=100.0, step=0.5)
            with row2_col4:
                enable_sl_target = st.checkbox("Attach Auto SL-L & Target", value=True)

            if enable_sl_target:
                sl_col1, sl_col2, sl_col3 = st.columns(3)
                with sl_col1:
                    sl_trigger_price = st.number_input("Stop-Loss Trigger (₹)", min_value=0.0, value=90.0, step=0.5)
                    sl_limit_price = st.number_input("Stop-Loss Limit Exit (₹)", min_value=0.0, value=89.5, step=0.5)
                with sl_col2:
                    target_limit_price = st.number_input("Target Limit Price (₹)", min_value=0.0, value=120.0, step=0.5)
                with sl_col3:
                    trailing_pts = st.number_input("Trailing SL Step (Points)", min_value=0.0, value=2.0, step=0.5)
                    st.caption("Auto-adjusts SL-L upwards as premium advances.")

            st.write("---")
            confirm_box = st.checkbox(f"I confirm to execute {order_side} order for {quantity} units of {symbol} at ₹{limit_price if order_type == 'LIMIT' else 'MARKET'}.")

            if st.button("🚀 TRANSMIT ORDER TO NSE", use_container_width=True, type="primary"):
                if confirm_box:
                    with st.spinner("Submitting order sequence to DhanHQ API..."):
                        try:
                            action = dhan_instance.BUY if order_side == "BUY" else dhan_instance.SELL
                            prod = dhan_instance.INTRA if "INTRADAY" in product_type else (dhan_instance.MARGIN if "FNO" in exchange_seg else dhan_instance.CNC)
                            seg = dhan_instance.NSE_FNO if "FNO" in exchange_seg else dhan_instance.NSE
                            otype = dhan_instance.LIMIT if order_type == "LIMIT" else dhan_instance.MARKET
                            
                            entry_resp = dhan_instance.place_order(
                                security_id=DHAN_SEC_IDS[symbol],
                                exchange_segment=seg,
                                transaction_type=action,
                                quantity=int(quantity),
                                order_type=otype,
                                product_type=prod,
                                price=float(limit_price) if order_type == "LIMIT" else 0
                            )

                            if entry_resp.get("status") == "success":
                                order_id = entry_resp.get("data", {}).get("orderId")
                                st.success(f"✅ Main Order Dispatched Successfully! Order ID: {order_id}")

                                if enable_sl_target:
                                    exit_side = dhan_instance.SELL if order_side == "BUY" else dhan_instance.BUY
                                    sl_resp = dhan_instance.place_order(
                                        security_id=DHAN_SEC_IDS[symbol],
                                        exchange_segment=seg,
                                        transaction_type=exit_side,
                                        quantity=int(quantity),
                                        order_type=dhan_instance.SL,
                                        product_type=prod,
                                        price=float(sl_limit_price),
                                        trigger_price=float(sl_trigger_price)
                                    )
                                    if sl_resp.get("status") == "success":
                                        st.success(f"🛡️ Auto SL-Limit Active! Trigger: ₹{sl_trigger_price}, Limit: ₹{sl_limit_price}")
                                    else:
                                        st.warning(f"SL Order Notice: {sl_resp.get('remarks')}")
                            else:
                                st.error(f"❌ Order Rejected: {entry_resp.get('remarks') or entry_resp.get('data')}")
                        except Exception as ex:
                            st.error(f"Transmission Exception: {str(ex)}")
                else:
                    st.warning("Please tick the confirmation checkbox prior to transmission.")

        # TAB 2: Live Positions
        with tab_pos:
            c_pnl1, c_pnl2 = st.columns([4, 1])
            with c_pnl1:
                st.metric("Total Unrealized MTM P&L", f"₹{total_pnl:.2f}", delta="MTM Status")
            with c_pnl2:
                if st.button("🔄 Refresh Positions", use_container_width=True):
                    st.rerun()

            try:
                positions_resp = dhan_instance.get_positions()
                if positions_resp and positions_resp.get("status") == "success" and positions_resp.get("data"):
                    open_positions = [p for p in positions_resp["data"] if p.get("netQty") != 0]
                    if open_positions:
                        pos_rows = []
                        for p in open_positions:
                            pos_rows.append({
                                "Security ID": p.get("securityId"),
                                "Trading Symbol": p.get("tradingSymbol"),
                                "Net Quantity": p.get("netQty"),
                                "Buy Avg Price (₹)": p.get("buyAvg"),
                                "LTP (₹)": p.get("lastPrice"),
                                "Unrealized P&L (₹)": p.get("unrealizedProfit"),
                                "Product": p.get("productType")
                            })
                        
                        df_pos = pd.DataFrame(pos_rows)
                        st.dataframe(df_pos, use_container_width=True, hide_index=True)

                        st.write("---")
                        st.subheader("Position Square-Off Console")
                        pos_symbols = [p["Trading Symbol"] for p in pos_rows]
                        target_exit_sym = st.selectbox("Select Position to Close", pos_symbols)
                        
                        col_ex1, col_ex2 = st.columns(2)
                        with col_ex1:
                            exit_mode = st.radio("Exit Execution Mode", ["LIMIT ORDER (Slip Protection)", "MARKET ORDER"], horizontal=True)
                        with col_ex2:
                            custom_exit_limit = st.number_input("Custom Exit Limit Price (₹)", min_value=0.0, value=100.0, step=0.5)

                        if st.button(f"⚡ Close Position: {target_exit_sym}", type="primary"):
                            pos_item = next(p for p in open_positions if p.get("tradingSymbol") == target_exit_sym)
                            exit_action = dhan_instance.SELL if pos_item.get("netQty") > 0 else dhan_instance.BUY
                            seg_type = dhan_instance.NSE_FNO if "OPT" in target_exit_sym else dhan_instance.NSE
                            
                            dhan_instance.place_order(
                                security_id=str(pos_item.get("securityId")),
                                exchange_segment=seg_type,
                                transaction_type=exit_action,
                                quantity=abs(int(pos_item.get("netQty"))),
                                order_type=dhan_instance.LIMIT if "LIMIT" in exit_mode else dhan_instance.MARKET,
                                product_type=dhan_instance.INTRA,
                                price=float(custom_exit_limit) if "LIMIT" in exit_mode else 0
                            )
                            st.success(f"Exit command dispatched for {target_exit_sym}")
                            st.rerun()
                    else:
                        st.info("No open positions active at this time.")
                else:
                    st.info("No open positions detected in your Dhan account.")
            except Exception as e:
                st.warning(f"Position Inquiry Error: {str(e)}")

        # TAB 3: Pending Orders
        with tab_pending:
            if st.button("🔄 Refresh Order Book", use_container_width=True):
                st.rerun()
            try:
                orders_resp = dhan_instance.get_order_list()
                if orders_resp and orders_resp.get("status") == "success" and orders_resp.get("data"):
                    pending_orders = [o for o in orders_resp["data"] if o.get("orderStatus") in ["PENDING", "TRANSIT", "TRIGGER_PENDING"]]
                    if pending_orders:
                        order_rows = []
                        for o in pending_orders:
                            order_rows.append({
                                "Order ID": o.get("orderId"),
                                "Trading Symbol": o.get("tradingSymbol"),
                                "Side": o.get("transactionType"),
                                "Quantity": o.get("quantity"),
                                "Order Type": o.get("orderType"),
                                "Limit Price (₹)": o.get("price"),
                                "Trigger Price (₹)": o.get("triggerPrice"),
                                "Status": o.get("orderStatus")
                            })
                        df_orders = pd.DataFrame(order_rows)
                        st.dataframe(df_orders, use_container_width=True, hide_index=True)
                    else:
                        st.info("No pending trigger/limit orders currently waiting.")
                else:
                    st.info("No active pending orders found.")
            except Exception as ex:
                st.warning(f"Order List Exception: {str(ex)}")

# ================= 7. TOP-TO-BOTTOM RESEARCH INTERFACE =================

# भाग 1: सभी इंडेक्स व सेक्टर्स का ट्रेंड
with st.expander("🏛️ भाग 1: सभी सेक्टर्स व इंडेक्स का लाइव ट्रेंड (तेजी vs मंदी)", expanded=False):
    st.write("**निफ्टी 50, बैंक निफ्टी, आईटी, ऑटो, मेटल, फार्मा, रियल्टी आदि का लाइव स्टेटस:**")
    if st.button("📊 सभी इंडेक्स व सेक्टर्स स्कैन करें", use_container_width=True, key="btn_scan_sectors"):
        with st.spinner("सभी 13 सेक्टर्स और इंडेक्स लोड हो रहे हैं..."):
            sec_results = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                res = executor.map(scan_sector_item, ALL_SECTOR_INDICES.items())
                for r in res:
                    if r: sec_results.append(r)
            if sec_results:
                sdf = pd.DataFrame(sec_results)
                st.dataframe(sdf, use_container_width=True, hide_index=True)

# भाग 2: मल्टी-फैक्टर टॉप 5 बुलिश और बेयरिश शेयर
with st.expander("⭐ भाग 2: टॉप 5 बुलिश और बेयरिश शेयर (मल्टी-फैक्टर विश्लेषण)", expanded=False):
    st.write("**तकनीकी आंकड़े (VWAP, PDH/PDL, 20 EMA) + ट्विटर पल्स + तिमाही नतीजे + खबरों के आधार पर टॉप 5:**")
    scan_limit = st.slider("स्कैन करने के लिए शेयरों की संख्या चुनें:", min_value=12, max_value=len(ALL_FNO_STOCKS), value=15, step=3)
    if st.button("🔥 मल्टी-फैक्टर मार्केट विश्लेषण शुरू करें", use_container_width=True, key="btn_deep_analysis"):
        with st.spinner(f"{scan_limit} शेयरों का मल्टी-फैक्टर स्कैन चल रहा है..."):
            stock_sublist = ALL_FNO_STOCKS[:scan_limit]
            analysis_data = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                items = executor.map(analyze_stock_full, stock_sublist)
                for itm in items:
                    if itm and itm["भाव (₹)"] > 0: analysis_data.append(itm)
            if analysis_data:
                mdf = pd.DataFrame(analysis_data)
                sorted_df = mdf.sort_values(by="कुल स्कोर", ascending=False)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.success("🟢 **शीर्ष बुलिश शेयर**")
                    st.dataframe(sorted_df.head(5)[["शेयर", "सेक्टर", "भाव (₹)", "तकनीकी रुझान", "कुल स्कोर"]], use_container_width=True, hide_index=True)
                with col_b:
                    st.error("🔴 **शीर्ष बेयरिश शेयर**")
                    st.dataframe(sorted_df.tail(5).iloc[::-1][["शेयर", "सेक्टर", "भाव (₹)", "तकनीकी रुझान", "कुल स्कोर"]], use_container_width=True, hide_index=True)

# भाग 3: तिमाही कॉर्पोरेट नतीजे व वर्डिक्ट
with st.expander("📊 भाग 3: कॉर्पोरेट रिजल्ट्स व अर्निंग्स वर्डिक्ट", expanded=False):
    if st.button("🔄 ताज़ा तिमाही नतीजे लोड करें", use_container_width=True, key="btn_res"):
        with st.spinner("वित्तीय नतीजों की समीक्षा हो रही है..."):
            res_list = fetch_rss_feed("quarterly+results+(profit+OR+loss+OR+pat+OR+revenue)+share+India", limit=15)
            if res_list:
                for r in res_list:
                    t = r['title'].lower()
                    is_bull = any(k in t for k in ["profit jumps", "pat rises", "beats estimates"])
                    is_bear = any(k in t for k in ["profit falls", "pat drops", "misses estimates"])
                    v_badge = "🟢 बुलिश" if is_bull else ("🔴 बेयरिश" if is_bear else "⚪ सामान्य")
                    st.markdown(f"**[{v_badge}]** `{r['stock']}` | [{r['title']}]({r['link']})")
                    st.divider()

# भाग 4: हाई-इम्पैक्ट बड़ी खबरें
with st.expander("⚡ भाग 4: बाज़ार हिलाने वाली बड़ी खबरें (High-Impact)", expanded=False):
    if st.button("🔄 सभी बड़ी मार्केट-मूविंग खबरें लोड करें", use_container_width=True, key="btn_impact"):
        with st.spinner("बड़ी खबरों को छांटा जा रहा है..."):
            news_list = fetch_rss_feed("(order+win+OR+penalty+OR+sebi+OR+usfda)+share+India", limit=15)
            if news_list:
                for n in news_list:
                    tl = n['title'].lower()
                    tag = "🟢 पॉजिटिव" if any(k in tl for k in ["order", "approval", "upgrade"]) else ("🔴 निगेटिव" if any(k in tl for k in ["penalty", "probe", "sebi"]) else "⚪ सामान्य")
                    st.markdown(f"**[{tag}]** `{n['stock']}` | [{n['title']}]({n['link']})")
                    st.divider()

# भाग 5: ज़ी बिज़नेस व सीएनबीसी आवाज़ रिसर्च
with st.expander("📺 भाग 5: ज़ी बिज़नेस व सीएनबीसी आवाज़ की सिफारिशें", expanded=False):
    if st.button("🔄 टीवी रिसर्च कॉल्स लोड करें", use_container_width=True, key="btn_tv"):
        with st.spinner("टीवी चैनल्स के रिसर्च कॉल्स लोड हो रहे हैं..."):
            tv_list = fetch_rss_feed("share+(Zee+Business+OR+CNBC+Awaaz+OR+Anil+Singhvi)+stock+buy+sell", limit=15)
            if tv_list:
                for t in tv_list:
                    src = "🟢 Zee Business" if "zee" in t['title'].lower() else ("🔵 CNBC Awaaz" if "cnbc" in t['title'].lower() else "📺 Business TV")
                    st.markdown(f"**[{src}]** `{t['stock']}` | [{t['title']}]({t['link']})")
                    st.divider()

# भाग 6: ब्रोकरेज हाउसेस के टारगेट्स
with st.expander("🎯 भाग 6: बड़े ब्रोकरेज हाउसेस के टारगेट प्राइस", expanded=False):
    if st.button("🔄 ब्रोकरेज टारगेट्स लोड करें", use_container_width=True, key="btn_brok"):
        with st.spinner("ब्रोकरेज रिपोर्ट्स फेच हो रही हैं..."):
            brok_list = fetch_rss_feed("brokerage+target+price+raised+OR+downgrade+share+India", limit=15)
            if brok_list:
                for b in brok_list:
                    tl = b['title'].lower()
                    call = "🟢 खरीदारी (Buy)" if any(w in tl for w in ["buy", "raised", "upgrade"]) else ("🔴 बिकवाली (Sell)" if any(w in tl for w in ["sell", "cut", "downgrade"]) else "⚪ अपडेट")
                    st.markdown(f"**[{call}]** `{b['stock']}` | [{b['title']}]({b['link']})")
                    st.divider()
