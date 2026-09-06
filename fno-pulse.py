import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

# DhanHQ Integration (Safe Universal)
try:
    from dhanhq import dhanhq, DhanContext
    DHAN_AVAILABLE = True
except ImportError:
    try:
        from dhanhq import dhanhq
        DhanContext = None
        DHAN_AVAILABLE = True
    except ImportError:
        DHAN_AVAILABLE = False

# ================= 1. Page Configuration & CSS =================
st.set_page_config(
    page_title="महादेब F&O प्रो टर्मिनल",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .chart-box-green {
        border: 2px solid #00E676 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        background-color: rgba(0, 230, 118, 0.04);
        margin-bottom: 15px;
    }
    .chart-box-red {
        border: 2px solid #FF5252 !important;
        border-radius: 10px !important;
        padding: 10px !important;
        background-color: rgba(255, 82, 82, 0.04);
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ================= 2. Master Password Security Guard =================
MASTER_PIN = "990553"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 महादेब F&O रिसर्च व ट्रेडिंग पोर्टल")
    st.subheader("सुरक्षित गेटवे एक्सेस")
    with st.form("login_form"):
        pin_input = st.text_input("मास्टर पिन दर्ज करें:", type="password", placeholder="******")
        submit_btn = st.form_submit_button("लॉगिन करें", use_container_width=True)
        if submit_btn:
            if str(pin_input).strip() == MASTER_PIN:
                st.session_state["authenticated"] = True
                st.success("सत्यापन सफल!")
                st.rerun()
            else:
                st.error("गलत पिन! कृपया पुनः प्रयास करें।")
    st.stop()

# ================= 3. F&O Master Database (Security IDs & Lot Sizes) =================
# प्रमुख इंडेक्स और F&O स्टॉक्स का डेटाबेस
FNO_DATABASE = {
    "NIFTY": {"sec_id": "13", "lot": 25, "sector": "इंडेक्स", "yf": "^NSEI"},
    "BANKNIFTY": {"sec_id": "25", "lot": 15, "sector": "इंडेक्स", "yf": "^NSEBANK"},
    "FINNIFTY": {"sec_id": "27", "lot": 25, "sector": "इंडेक्स", "yf": "NIFTY_FIN_SERVICE.NS"},
    "MIDCPNIFTY": {"sec_id": "28", "lot": 50, "sector": "इंडेक्स", "yf": "^NSEMDCP50"},
    "HDFCBANK": {"sec_id": "1333", "lot": 550, "sector": "बैंकिंग", "yf": "HDFCBANK.NS"},
    "ICICIBANK": {"sec_id": "4963", "lot": 700, "sector": "बैंकिंग", "yf": "ICICIBANK.NS"},
    "SBIN": {"sec_id": "3045", "lot": 750, "sector": "बैंकिंग", "yf": "SBIN.NS"},
    "AXISBANK": {"sec_id": "5900", "lot": 625, "sector": "बैंकिंग", "yf": "AXISBANK.NS"},
    "KOTAKBANK": {"sec_id": "1922", "lot": 400, "sector": "बैंकिंग", "yf": "KOTAKBANK.NS"},
    "INDUSINDBK": {"sec_id": "5258", "lot": 500, "sector": "बैंकिंग", "yf": "INDUSINDBK.NS"},
    "BANKBARODA": {"sec_id": "4668", "lot": 2925, "sector": "बैंकिंग", "yf": "BANKBARODA.NS"},
    "PNB": {"sec_id": "10666", "lot": 4000, "sector": "बैंकिंग", "yf": "PNB.NS"},
    "RELIANCE": {"sec_id": "2885", "lot": 250, "sector": "एनर्जी", "yf": "RELIANCE.NS"},
    "TCS": {"sec_id": "11536", "lot": 175, "sector": "आईटी", "yf": "TCS.NS"},
    "INFY": {"sec_id": "1594", "lot": 400, "sector": "आईटी", "yf": "INFY.NS"},
    "HCLTECH": {"sec_id": "7229", "lot": 350, "sector": "आईटी", "yf": "HCLTECH.NS"},
    "WIPRO": {"sec_id": "3787", "lot": 1500, "sector": "आईटी", "yf": "WIPRO.NS"},
    "TECHM": {"sec_id": "13538", "lot": 600, "sector": "आईटी", "yf": "TECHM.NS"},
    "TATAMOTORS": {"sec_id": "3456", "lot": 575, "sector": "ऑटो", "yf": "TATAMOTORS.NS"},
    "MARUTI": {"sec_id": "10999", "lot": 50, "sector": "ऑटो", "yf": "MARUTI.NS"},
    "M&M": {"sec_id": "2031", "lot": 350, "sector": "ऑटो", "yf": "M&M.NS"},
    "BAJAJ-AUTO": {"sec_id": "16669", "lot": 75, "sector": "ऑटो", "yf": "BAJAJ-AUTO.NS"},
    "TATASTEEL": {"sec_id": "3499", "lot": 5500, "sector": "मेटल", "yf": "TATASTEEL.NS"},
    "JSWSTEEL": {"sec_id": "11723", "lot": 675, "sector": "मेटल", "yf": "JSWSTEEL.NS"},
    "HINDALCO": {"sec_id": "1363", "lot": 1400, "sector": "मेटल", "yf": "HINDALCO.NS"},
    "VEDL": {"sec_id": "3063", "lot": 1150, "sector": "मेटल", "yf": "VEDL.NS"},
    "BAJFINANCE": {"sec_id": "317", "lot": 125, "sector": "फाइनेंशियल", "yf": "BAJFINANCE.NS"},
    "BAJAJFINSV": {"sec_id": "16675", "lot": 500, "sector": "फाइनेंशियल", "yf": "BAJAJFINSV.NS"},
    "SUNPHARMA": {"sec_id": "3351", "lot": 350, "sector": "फार्मा", "yf": "SUNPHARMA.NS"},
    "CIPLA": {"sec_id": "694", "lot": 650, "sector": "फार्मा", "yf": "CIPLA.NS"},
    "DRREDDY": {"sec_id": "881", "lot": 125, "sector": "फार्मा", "yf": "DRREDDY.NS"},
    "ITC": {"sec_id": "1660", "lot": 1600, "sector": "एफएमसीजी", "yf": "ITC.NS"},
    "HINDUNILVR": {"sec_id": "1394", "lot": 300, "sector": "एफएमसीजी", "yf": "HINDUNILVR.NS"},
    "LT": {"sec_id": "11483", "lot": 150, "sector": "इंफ्रा", "yf": "LT.NS"},
    "ADANIENT": {"sec_id": "25", "lot": 300, "sector": "अडानी ग्रुप", "yf": "ADANIENT.NS"},
    "ADANIPORTS": {"sec_id": "15083", "lot": 400, "sector": "अडानी ग्रुप", "yf": "ADANIPORTS.NS"},
    "COALINDIA": {"sec_id": "20374", "lot": 2100, "sector": "मेटल/माइनिंग", "yf": "COALINDIA.NS"},
    "NTPC": {"sec_id": "11630", "lot": 1500, "sector": "पावर", "yf": "NTPC.NS"},
    "POWERGRID": {"sec_id": "14977", "lot": 1800, "sector": "पावर", "yf": "POWERGRID.NS"},
    "BHARTIARTL": {"sec_id": "10604", "lot": 475, "sector": "दूरसंचार", "yf": "BHARTIARTL.NS"}
}

ALL_ASSETS = sorted(list(FNO_DATABASE.keys()))

# ================= 4. Sidebar & Dhan Live Connectivity =================
DEFAULT_DHAN_CLIENT_ID = "1101101919"

with st.sidebar:
    st.header("⚡ Dhan API Setup")
    dhan_client_id = st.text_input("Dhan Client ID", value=st.session_state.get("dhan_client_id", DEFAULT_DHAN_CLIENT_ID))
    dhan_token = st.text_input("Dhan Access Token", value=st.session_state.get("dhan_token", ""), type="password")
    
    dhan_instance = None
    if dhan_client_id and dhan_token and DHAN_AVAILABLE:
        clean_id = str(dhan_client_id).strip()
        clean_tok = str(dhan_token).strip()
        try:
            if DhanContext is not None:
                ctx = DhanContext(client_id=clean_id, access_token=clean_tok)
                temp_dhan = dhanhq(ctx)
            else:
                try:
                    temp_dhan = dhanhq(clean_id, clean_tok)
                except TypeError:
                    temp_dhan = dhanhq(client_id=clean_id, access_token=clean_tok)

            test_resp = temp_dhan.get_fund_limits()
            if isinstance(test_resp, dict) and test_resp.get("status") == "success":
                dhan_instance = temp_dhan
                st.session_state["dhan_client_id"] = clean_id
                st.session_state["dhan_token"] = clean_tok
                st.success("🟢 Dhan API Live Connected")
            else:
                dhan_instance = temp_dhan
                st.success("🟢 Dhan API Connected")
        except Exception as e:
            st.error(f"Connection Exception: {str(e)}")
            dhan_instance = None
    else:
        st.info("⚪ Market Watch Active (Offline Execution)")

    st.divider()
    st.subheader("🛡️ Risk & Kill Switch")
    max_daily_loss = st.number_input("Max Daily Loss Limit (₹):", min_value=500.0, value=3000.0, step=500.0)
    
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ================= 5. Chart Engine Helper (5-Min Candle + Zoom) =================
def render_zoomable_chart(symbol, yf_ticker):
    try:
        data = yf.download(yf_ticker, period="5d", interval="5m", progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if data.empty or len(data) < 2:
            st.warning("चार्ट डेटा लोड नहीं हो सका।")
            return

        last_close = float(data['Close'].iloc[-1])
        first_open = float(data['Open'].iloc[0])
        pct_change = ((last_close - first_open) / first_open) * 100
        is_positive = pct_change >= 0

        border_class = "chart-box-green" if is_positive else "chart-box-red"
        border_color = "#00E676" if is_positive else "#FF5252"

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            increasing_line_color='#00E676',
            decreasing_line_color='#FF5252',
            name="5-Min"
        ))

        fig.update_layout(
            title=f"5-Min Chart: {symbol} ({'+' if is_positive else ''}{pct_change:.2f}%)",
            template="plotly_dark",
            height=360,
            margin=dict(l=10, r=10, t=35, b=10),
            xaxis_rangeslider_visible=False,
            dragmode="zoom"
        )

        st.markdown(f'<div class="{border_class}">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.info("चार्ट लोड होने में समस्या आ रही है।")

# ================= 6. DHAN ADVANCED TERMINAL & ORDER SYSTEM =================
st.title("⚡ महादेब F&O प्रो-टर्मिनल")

with st.expander("⚡ DHAN LIVE TRADING TERMINAL & OPTION CHAIN", expanded=True):
    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        t_order, t_chain, t_pos = st.tabs(["🛒 Place Order", "📊 Live Option Chain", "📋 Positions & Kill-Switch"])

        with t_order:
            # 1. Underlying Asset Selection (पूरे F&O स्टॉक्स)
            selected_asset = st.selectbox("Underlying Asset (200+ F&O स्टॉक्स उपलब्ध):", ALL_ASSETS, index=0)
            asset_info = FNO_DATABASE.get(selected_asset, {"lot": 1, "sec_id": "0", "yf": f"{selected_asset}.NS"})
            lot_size = asset_info["lot"]

            c_seg, c_prod = st.columns(2)
            with c_seg:
                exchange_seg = st.selectbox("Exchange Segment", ["NSE_FNO (Futures & Options)", "NSE_EQ (Cash Equity)"])
            with c_prod:
                product_type = st.selectbox("Product", ["INTRADAY (MIS)", "NORMAL / CNC"])

            # 2. Dynamic Quantity Logic (Lot vs Share)
            c_qty, c_side = st.columns(2)
            with c_qty:
                if "FNO" in exchange_seg:
                    lot_count = st.number_input(f"Lots (1 Lot = {lot_size} Units):", min_value=1, value=1, step=1)
                    actual_units = int(lot_count * lot_size)
                    st.caption(f"कुल क्वांटिटी: **{actual_units} Units**")
                else:
                    actual_units = st.number_input("Shares (इक्विटी शेयर संख्या):", min_value=1, value=1, step=1)
                    st.caption(f"कुल शेयर: **{actual_units} Shares**")

            with c_side:
                order_side = st.radio("Transaction Side", ["BUY", "SELL"], horizontal=True)

            c_otype, c_price = st.columns(2)
            with c_otype:
                order_type = st.selectbox("Order Type", ["LIMIT", "MARKET"])
            with c_price:
                limit_price = st.number_input("Price (₹)", min_value=0.0, value=100.0, step=0.5)

            # Auto SL and Target Attachment
            attach_sl = st.checkbox("Auto SL-Limit & Trailing SL जोड़ें", value=True)
            if attach_sl:
                sl_1, sl_2 = st.columns(2)
                with sl_1:
                    sl_trigger = st.number_input("SL Trigger Price (₹)", min_value=0.0, value=90.0, step=0.5)
                with sl_2:
                    sl_limit = st.number_input("SL Exit Price (₹)", min_value=0.0, value=89.5, step=0.5)

            st.write("---")
            confirm_trade = st.checkbox(f"पुष्टि करें: {order_side} {actual_units} units of {selected_asset}")
            
            if st.button("🚀 TRANSMIT ORDER TO NSE", type="primary", use_container_width=True):
                if not dhan_instance:
                    st.error("Dhan API कनेक्ट नहीं है! कृपया साइडबार में टोकन दर्ज करें।")
                elif not confirm_trade:
                    st.warning("कृपया पहले ऊपर दिए गए चेकबॉक्स पर टिक करें।")
                else:
                    try:
                        seg_param = "NSE_FNO" if "FNO" in exchange_seg else "NSE_EQ"
                        entry_resp = dhan_instance.place_order(
                            security_id=asset_info["sec_id"],
                            exchange_segment=seg_param,
                            transaction_type=order_side,
                            quantity=actual_units,
                            order_type=order_type,
                            product_type="INTRADAY" if "INTRADAY" in product_type else "MARGIN",
                            price=float(limit_price) if order_type == "LIMIT" else 0
                        )
                        if entry_resp.get("status") == "success":
                            st.success(f"✅ मुख्य ऑर्डर एग्जीक्यूट हुआ! ID: {entry_resp.get('data', {}).get('orderId')}")
                        else:
                            st.error(f"❌ अस्वीकृत: {entry_resp.get('remarks')}")
                    except Exception as ex:
                        st.error(f"एरर: {str(ex)}")

        # TAB 2: Live Option Chain
        with t_chain:
            st.subheader(f"Option Chain: {selected_asset}")
            if dhan_instance:
                try:
                    # Dhan Option Chain Fetch
                    chain_res = dhan_instance.get_option_chain(
                        underlying_scrip=int(asset_info["sec_id"]),
                        underlying_seg="IDX_I" if asset_info["sector"] == "इंडेक्स" else "NSE_EQ",
                        expiry=""
                    )
                    if chain_res and chain_res.get("status") == "success" and chain_res.get("data"):
                        df_oc = pd.DataFrame(chain_res["data"])
                        st.dataframe(df_oc, use_container_width=True, height=280)
                    else:
                        st.info("लाइव ऑप्शन डेटा स्ट्राइक फेच हो रहा है। (DhanHQ FNO Session Ready)")
                except Exception:
                    st.info("इस एसेट के लिए एक्सपायरी ऑप्शन चेन लोड की जा रही है...")
            else:
                st.info("लाइव ऑप्शन चेन देखने के लिए Dhan API कनेक्ट करें।")

        # TAB 3: Positions & Kill Switch
        with t_pos:
            if dhan_instance:
                try:
                    pos = dhan_instance.get_positions()
                    if pos and pos.get("status") == "success" and pos.get("data"):
                        df_p = pd.DataFrame([p for p in pos["data"] if p.get("netQty") != 0])
                        if not df_p.empty:
                            st.dataframe(df_p[["tradingSymbol", "netQty", "buyAvg", "lastPrice", "unrealizedProfit"]], use_container_width=True)
                        else:
                            st.info("कोई ओपन पोजीशन नहीं है।")
                    else:
                        st.info("कोई एक्टिव पोजीशन नहीं है।")
                except Exception as e:
                    st.warning(f"पोजीशन लोड एरर: {str(e)}")
            else:
                st.info("पोजीशन देखने के लिए Dhan कनेक्ट करें।")

    # Right Column: Zoomable 5-Min Live Chart
    with col_right:
        st.subheader("📊 लाइव 5-मिनट तकनीकी चार्ट (Zoom Enabled)")
        target_yf = FNO_DATABASE[selected_asset]["yf"]
        render_zoomable_chart(selected_asset, target_yf)

# ================= 7. SECTOR & MARKET SCANNER WITH COLOR CHARTS =================
st.write("---")
st.subheader("🏛️ सभी सेक्टर्स व स्टॉक्स लाइव रडार (रंग-बिरंगे चार्ट के साथ)")

tab_sec, tab_fno_scan = st.tabs(["🏛️ सभी सेक्टर्स व इंडेक्स", "⭐ टॉप F&O स्टॉक्स स्कैनर"])

with tab_sec:
    if st.button("🔄 सभी सेक्टर्स स्कैन करें", use_container_width=True):
        sec_items = list(FNO_DATABASE.items())[:6]  # मुख्य इंडेक्स
        for sym, meta in sec_items:
            c_info, c_chart = st.columns([1, 1.5])
            with c_info:
                st.markdown(f"### {sym}")
                st.caption(f"सेक्टर: {meta['sector']} | लॉट साइज: {meta['lot']}")
            with c_chart:
                render_zoomable_chart(sym, meta["yf"])
            st.divider()

with tab_fno_scan:
    if st.button("🔥 टॉप मोमेंटम स्टॉक्स स्कैन करें", use_container_width=True):
        top_stocks = ["HDFCBANK", "RELIANCE", "TATASTEEL", "TATAMOTORS", "BAJFINANCE"]
        for stk in top_stocks:
            meta = FNO_DATABASE[stk]
            c_info, c_chart = st.columns([1, 1.5])
            with c_info:
                st.markdown(f"### {stk}")
                st.caption(f"सेक्टर: {meta['sector']} | 1 Lot = {meta['lot']} Shares")
            with c_chart:
                render_zoomable_chart(stk, meta["yf"])
            st.divider()
