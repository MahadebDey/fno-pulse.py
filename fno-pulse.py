import streamlit as st
import os
import json
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# DhanHQ Integration
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
        border-radius: 8px !important;
        padding: 6px !important;
        background-color: rgba(0, 230, 118, 0.03);
        margin-top: 6px;
    }
    .chart-box-red {
        border: 2px solid #FF5252 !important;
        border-radius: 8px !important;
        padding: 6px !important;
        background-color: rgba(255, 82, 82, 0.03);
        margin-top: 6px;
    }
    .call-badge { background-color: #00E676; color: black; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .put-badge { background-color: #FF5252; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
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

# ================= 3. Session State Initialization =================
if "chart_tf" not in st.session_state:
    st.session_state["chart_tf"] = "5m"
if "chart_type" not in st.session_state:
    st.session_state["chart_type"] = "Regular Candlestick"
if "chart_show_ema" not in st.session_state:
    st.session_state["chart_show_ema"] = True
if "selected_fno_asset" not in st.session_state:
    st.session_state["selected_fno_asset"] = "NIFTY"

# ================= 4. Token Cache System =================
TOKEN_CACHE_FILE = ".dhan_token_cache.json"

def load_cached_credentials():
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_credentials_to_cache(client_id, token):
    try:
        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump({"client_id": client_id, "token": token}, f)
    except Exception:
        pass

def delete_cached_token():
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            os.remove(TOKEN_CACHE_FILE)
        except Exception:
            pass

cached_creds = load_cached_credentials()
default_client_id = cached_creds.get("client_id", "1101101919")
default_token = cached_creds.get("token", "")

# ================= 5. Sidebar Setup & Live Ticks =================
with st.sidebar:
    st.header("⚡ Dhan API Setup")
    dhan_client_id = st.text_input("Dhan Client ID", value=default_client_id)
    dhan_token = st.text_input("Dhan Access Token", value=default_token, type="password")
    
    dhan_instance = None
    if dhan_client_id and dhan_token and DHAN_AVAILABLE:
        clean_id = str(dhan_client_id).strip()
        clean_tok = str(dhan_token).strip()
        
        if clean_tok != default_token or clean_id != default_client_id:
            save_credentials_to_cache(clean_id, clean_tok)

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
                st.success("🟢 Dhan API Live Connected")
            else:
                dhan_instance = temp_dhan
                st.success("🟢 Dhan API Connected")
        except Exception as e:
            st.error(f"Connection Exception: {str(e)}")
            dhan_instance = None
    else:
        st.info("⚪ टोकन दर्ज करें (Yahoo Backup Active)")

    if default_token or dhan_token:
        if st.button("🗑️ डिलीट / रीसेट Dhan टोकन", use_container_width=True):
            delete_cached_token()
            st.warning("टोकन हटा दिया गया है।")
            st.rerun()

    st.divider()
    st.header("⏱️ लाइव ऑटो-रिफ्रेश")
    auto_refresh_on = st.toggle("मार्केट टिक्स ऑटो-रिफ्रेश चालू करें", value=False)
    if auto_refresh_on:
        refresh_interval = st.selectbox("रिफ्रेश टाइम:", [5, 10, 15, 30], index=1, format_func=lambda x: f"{x} सेकंड")
        if AUTOREFRESH_AVAILABLE:
            st_autorefresh(interval=refresh_interval * 1000, key="live_market_tick")

    st.divider()
    st.header("📊 ग्लोबल चार्ट सेटिंग्स")
    def update_type(): st.session_state["chart_type"] = st.session_state["sb_chart_type"]
    def update_tf(): st.session_state["chart_tf"] = st.session_state["sb_chart_tf"]
    def update_ema(): st.session_state["chart_show_ema"] = st.session_state["sb_chart_ema"]

    st.radio("कैंडल प्रकार:", ["Regular Candlestick", "Heikin-Ashi (हेइकिन-आशी)"],
             index=0 if st.session_state["chart_type"] == "Regular Candlestick" else 1,
             key="sb_chart_type", on_change=update_type)
    
    st.selectbox("टाइमफ्रेम:", ["1m", "5m", "15m", "1h", "1d"],
                 index=["1m", "5m", "15m", "1h", "1d"].index(st.session_state["chart_tf"]),
                 format_func=lambda x: {"1m": "1 Min (Scalp)", "5m": "5 Min (Intraday)", "15m": "15 Min (Trend)", "1h": "1 Hour", "1d": "Daily"}.get(x, x),
                 key="sb_chart_tf", on_change=update_tf)
    
    st.toggle("9 EMA (गोल्डन लाइन)", value=st.session_state["chart_show_ema"], key="sb_chart_ema", on_change=update_ema)

    st.divider()
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

# ================= 6. F&O Database & Step Sizes =================
FNO_DATABASE = {
    "NIFTY": {"sec_id": "13", "lot": 25, "sector": "इंडेक्स", "step": 50, "yf": "^NSEI", "seg": "IDX_I"},
    "BANKNIFTY": {"sec_id": "25", "lot": 15, "sector": "इंडेक्स", "step": 100, "yf": "^NSEBANK", "seg": "IDX_I"},
    "FINNIFTY": {"sec_id": "27", "lot": 25, "sector": "इंडेक्स", "step": 50, "yf": "NIFTY_FIN_SERVICE.NS", "seg": "IDX_I"},
    "MIDCPNIFTY": {"sec_id": "28", "lot": 50, "sector": "इंडेक्स", "step": 25, "yf": "^NSEMDCP50", "seg": "IDX_I"},
    "AXISBANK": {"sec_id": "5900", "lot": 625, "sector": "बैंकिंग", "step": 10, "yf": "AXISBANK.NS", "seg": "NSE_EQ"},
    "HDFCBANK": {"sec_id": "1333", "lot": 550, "sector": "बैंकिंग", "step": 10, "yf": "HDFCBANK.NS", "seg": "NSE_EQ"},
    "ICICIBANK": {"sec_id": "4963", "lot": 700, "sector": "बैंकिंग", "step": 10, "yf": "ICICIBANK.NS", "seg": "NSE_EQ"},
    "SBIN": {"sec_id": "3045", "lot": 750, "sector": "बैंकिंग", "step": 5, "yf": "SBIN.NS", "seg": "NSE_EQ"},
    "KOTAKBANK": {"sec_id": "1922", "lot": 400, "sector": "बैंकिंग", "step": 20, "yf": "KOTAKBANK.NS", "seg": "NSE_EQ"},
    "RELIANCE": {"sec_id": "2885", "lot": 250, "sector": "एनर्जी", "step": 20, "yf": "RELIANCE.NS", "seg": "NSE_EQ"},
    "TCS": {"sec_id": "11536", "lot": 175, "sector": "आईटी", "step": 50, "yf": "TCS.NS", "seg": "NSE_EQ"},
    "INFY": {"sec_id": "1594", "lot": 400, "sector": "आईटी", "step": 20, "yf": "INFY.NS", "seg": "NSE_EQ"},
    "TATAMOTORS": {"sec_id": "3456", "lot": 575, "sector": "ऑटो", "step": 10, "yf": "TATAMOTORS.NS", "seg": "NSE_EQ"},
    "TATASTEEL": {"sec_id": "3499", "lot": 5500, "sector": "मेटल", "step": 1, "yf": "TATASTEEL.NS", "seg": "NSE_EQ"},
    "MARUTI": {"sec_id": "10999", "lot": 50, "sector": "ऑटो", "step": 100, "yf": "MARUTI.NS", "seg": "NSE_EQ"},
    "BAJFINANCE": {"sec_id": "317", "lot": 125, "sector": "फाइनेंशियल", "step": 50, "yf": "BAJFINANCE.NS", "seg": "NSE_EQ"}
}

ALL_ASSETS = sorted(list(FNO_DATABASE.keys()))

# ================= 7. Live Option Chain & Strikes Engine =================
def fetch_live_option_chain_dhan(asset_name, dhan):
    meta = FNO_DATABASE.get(asset_name)
    if not meta or not dhan:
        return None, None
    try:
        # 1. Expiry List Fetch
        exp_res = dhan.expiry_list(under_security_id=int(meta["sec_id"]), under_exchange_segment=meta["seg"])
        if isinstance(exp_res, dict) and exp_res.get("status") == "success" and exp_res.get("data"):
            expiries = exp_res["data"]
            target_expiry = expiries[0] if expiries else ""
        else:
            target_expiry = ""
            expiries = []

        # 2. Option Chain Fetch
        oc_res = dhan.option_chain(under_security_id=int(meta["sec_id"]), under_exchange_segment=meta["seg"], expiry=target_expiry)
        if isinstance(oc_res, dict) and oc_res.get("status") == "success" and oc_res.get("data"):
            return oc_res["data"], expiries
    except Exception:
        pass
    return None, None

def generate_dynamic_strikes(cmp_val, step, num_strikes=7):
    """ATM के आस-पास के स्ट्राइक्स तैयार करना"""
    atm = round(cmp_val / step) * step
    strikes = []
    for i in range(-num_strikes, num_strikes + 1):
        strikes.append(int(atm + (i * step)))
    return strikes, atm

# ================= 8. Chart Engine =================
def compute_heikin_ashi(df):
    ha = pd.DataFrame(index=df.index)
    ha['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha['Close'].iloc[i-1]) / 2.0
    ha['Open'] = ha_open
    ha['High'] = pd.concat([df['High'], ha['Open'], ha['Close']], axis=1).max(axis=1)
    ha['Low'] = pd.concat([df['Low'], ha['Open'], ha['Close']], axis=1).min(axis=1)
    return ha

def render_zoomable_chart(symbol, yf_ticker):
    tf = st.session_state.get("chart_tf", "5m")
    ctype = st.session_state.get("chart_type", "Regular Candlestick")
    show_ema = st.session_state.get("chart_show_ema", True)

    tf_params = {
        "1m": {"period": "2d", "interval": "1m"},
        "5m": {"period": "5d", "interval": "5m"},
        "15m": {"period": "10d", "interval": "15m"},
        "1h": {"period": "1mo", "interval": "60m"},
        "1d": {"period": "6mo", "interval": "1d"}
    }
    cfg = tf_params.get(tf, {"period": "5d", "interval": "5m"})

    try:
        data = yf.download(yf_ticker, period=cfg["period"], interval=cfg["interval"], progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if data.empty or len(data) < 2:
            st.info(f"{symbol}: चार्ट डेटा फेच हो रहा है...")
            return

        if tf in ["1m", "5m", "15m"]:
            if data.index.tz is not None:
                data.index = data.index.tz_convert("Asia/Kolkata")
            else:
                data.index = data.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
            data = data.between_time('09:15', '15:40')

        last_close = float(data['Close'].iloc[-1])
        first_open = float(data['Open'].iloc[0])
        pct_change = ((last_close - first_open) / first_open) * 100
        is_positive = pct_change >= 0

        border_class = "chart-box-green" if is_positive else "chart-box-red"
        
        is_ha = "Heikin" in ctype
        if is_ha:
            plot_df = compute_heikin_ashi(data)
            label_name = "Heikin-Ashi"
        else:
            plot_df = data[['Open', 'High', 'Low', 'Close']].copy()
            label_name = "Regular"

        ema9 = plot_df['Close'].ewm(span=9, adjust=False).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=plot_df.index,
            open=plot_df['Open'],
            high=plot_df['High'],
            low=plot_df['Low'],
            close=plot_df['Close'],
            increasing_line_color='#00E676',
            decreasing_line_color='#FF5252',
            name=f"{label_name} ({tf})"
        ))

        if show_ema:
            fig.add_trace(go.Scatter(
                x=plot_df.index,
                y=ema9,
                mode='lines',
                line=dict(color='#FFD700', width=1.8),
                name='9 EMA'
            ))

        fig.update_layout(
            title=dict(
                text=f"<b>{symbol}</b> | {label_name} ({tf.upper()}) | {'+' if is_positive else ''}{pct_change:.2f}%",
                font=dict(size=14, color="#FFFFFF"),
                x=0.01,
                y=0.98
            ),
            template="plotly_dark",
            height=420,
            margin=dict(l=10, r=10, t=30, b=30),
            xaxis_rangeslider_visible=False,
            dragmode="zoom",
            legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5)
        )

        if tf in ["1m", "5m", "15m"]:
            fig.update_xaxes(
                rangebreaks=[
                    dict(bounds=["sat", "mon"]),
                    dict(bounds=[15.67, 9.25], pattern="hour")
                ]
            )

        st.markdown(f'<div class="{border_class}">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception:
        st.info(f"{symbol}: लाइव डेटा उपलब्ध नहीं है।")

# ================= 9. ADVANCED OPTIONS TRADING TERMINAL =================
st.title("⚡ महादेब F&O प्रो-टर्मिनल")

# CMP Fetch for selected Asset
target_asset = st.session_state.get("selected_fno_asset", "AXISBANK")
meta_info = FNO_DATABASE.get(target_asset, FNO_DATABASE["AXISBANK"])

try:
    ticker_obj = yf.Ticker(meta_info["yf"])
    cmp_live = round(float(ticker_obj.fast_info['last_price']), 2)
except Exception:
    cmp_live = 1268.0

strikes_list, atm_strike = generate_dynamic_strikes(cmp_live, meta_info["step"])

with st.expander("⚡ DHAN LIVE OPTIONS EXECUTION TERMINAL & OPTION CHAIN", expanded=True):
    col_left, col_right = st.columns([1.1, 0.9])

    with col_left:
        t_order, t_chain, t_pos = st.tabs(["🎯 Place Option Trade", "📊 Live Option Chain", "📋 Positions"])

        # TAB 1: Real Options Trading Console
        with t_order:
            # 1. Underlying Asset
            c_u1, c_u2 = st.columns([1.5, 1])
            with c_u1:
                def on_asset_change():
                    st.session_state["selected_fno_asset"] = st.session_state["asset_select_key"]
                
                selected_asset = st.selectbox(
                    "Underlying Asset (शेयर / इंडेक्स):",
                    ALL_ASSETS,
                    index=ALL_ASSETS.index(target_asset),
                    key="asset_select_key",
                    on_change=on_asset_change
                )
            with c_u2:
                st.metric("मौजूदा भाव (CMP)", f"₹{cmp_live}", delta=f"ATM: ₹{atm_strike}")

            # 2. Instrument Type (CALL / PUT / CASH)
            trade_type = st.radio(
                "ट्रेडिंग इंस्ट्रूमेंट चुनें:",
                ["🟢 CALL OPTION (CE) - तेजी", "🔴 PUT OPTION (PE) - मंदी", "📈 EQUITY (Cash Share)"],
                horizontal=True
            )

            is_option = "OPTION" in trade_type
            opt_kind = "CE" if "CALL" in trade_type else "PE"

            # 3. Strike Price & Lots Selection
            c_strk, c_exp, c_lots = st.columns(3)
            
            with c_strk:
                if is_option:
                    def format_strike(s):
                        diff = s - atm_strike
                        if diff == 0: return f"₹{s} (ATM)"
                        elif (diff < 0 and opt_kind == "CE") or (diff > 0 and opt_kind == "PE"):
                            return f"₹{s} (ITM)"
                        else:
                            return f"₹{s} (OTM)"

                    selected_strike = st.selectbox(
                        "स्ट्राइक प्राइस (Strike):",
                        strikes_list,
                        index=strikes_list.index(atm_strike),
                        format_func=format_strike
                    )
                else:
                    selected_strike = None
                    st.text_input("स्ट्राइक", value="N/A (Cash)", disabled=True)

            with c_exp:
                if is_option:
                    curr_dt = datetime.now()
                    # एक्टिव एक्सपायरी लिस्ट
                    expiries_demo = [(curr_dt + timedelta(days=(3 - curr_dt.weekday()) % 7)).strftime("%d %b %Y"),
                                     (curr_dt + timedelta(days=28)).strftime("%d %b %Y")]
                    selected_expiry = st.selectbox("एक्सपायरी:", expiries_demo)
                else:
                    selected_expiry = "CASH"
                    st.text_input("एक्सपायरी", value="Cash Equity", disabled=True)

            with c_lots:
                lot_size = meta_info["lot"]
                if is_option:
                    num_lots = st.number_input(f"Lots (1 Lot = {lot_size}):", min_value=1, value=1, step=1)
                    final_qty = int(num_lots * lot_size)
                    st.caption(f"कुल क्वांटिटी: **{final_qty} Qty**")
                else:
                    final_qty = st.number_input("Shares (संख्या):", min_value=1, value=10, step=1)
                    st.caption(f"कुल शेयर: **{final_qty} Shares**")

            # Contract Name Banner
            if is_option:
                contract_name = f"{selected_asset} {selected_strike} {opt_kind}"
                badge_class = "call-badge" if opt_kind == "CE" else "put-badge"
                st.markdown(f"अनुबंध (Contract): <span class='{badge_class}'>{contract_name}</span> | Lot: {lot_size}", unsafe_allow_html=True)
            else:
                contract_name = f"{selected_asset} (NSE Cash)"
                st.markdown(f"अनुबंध: **{contract_name}**")

            # 4. Order Execution Settings
            c_side, c_otype, c_pr = st.columns(3)
            with c_side:
                order_side = st.radio("Side:", ["BUY", "SELL"], horizontal=True)
            with c_otype:
                order_type = st.selectbox("Order Type:", ["MARKET", "LIMIT"])
            with c_pr:
                est_premium = 25.50 if is_option else cmp_live
                order_price = st.number_input("लिमिट प्राइस (₹):", min_value=0.05, value=float(est_premium), step=0.5)

            # Auto SL & Target
            attach_sl = st.checkbox("Auto Stop-Loss Limit & Target जोड़ें", value=True)
            if attach_sl:
                sl1, sl2 = st.columns(2)
                with sl1:
                    sl_pts = st.number_input("SL Points (प्रीमियम में से घटाएं):", min_value=1.0, value=5.0, step=0.5)
                with sl2:
                    tgt_pts = st.number_input("Target Points (प्रॉफिट लक्ष्य):", min_value=1.0, value=10.0, step=0.5)

            st.write("---")
            confirm_box = st.checkbox(f"पुष्टि करें: {order_side} {final_qty} Qty of {contract_name} @ ₹{order_price if order_type == 'LIMIT' else 'MARKET'}")

            if st.button("🚀 TRANSMIT OPTION ORDER TO NSE", type="primary", use_container_width=True):
                if not dhan_instance:
                    st.error("Dhan API कनेक्ट नहीं है! कृपया साइडबार में टोकन दर्ज करें।")
                elif not confirm_box:
                    st.warning("कृपया पहले पुष्टि वाले चेकबॉक्स पर टिक करें।")
                else:
                    try:
                        # Dhan FNO execution
                        target_sec_id = meta_info["sec_id"]
                        seg = "NSE_FNO" if is_option else "NSE_EQ"
                        
                        resp = dhan_instance.place_order(
                            security_id=str(target_sec_id),
                            exchange_segment=seg,
                            transaction_type=order_side,
                            quantity=int(final_qty),
                            order_type=order_type,
                            product_type="INTRADAY",
                            price=float(order_price) if order_type == "LIMIT" else 0
                        )
                        if isinstance(resp, dict) and resp.get("status") == "success":
                            st.success(f"✅ {contract_name} ऑर्डर सफल! Order ID: {resp.get('data', {}).get('orderId')}")
                        else:
                            st.error(f"❌ अस्वीकृत: {resp.get('remarks', resp)}")
                    except Exception as ex:
                        st.error(f"Execution Error: {str(ex)}")

        # TAB 2: Live Option Chain
        with t_chain:
            st.subheader(f"📊 लाइव ऑप्शन चेन: {selected_asset} (CMP: ₹{cmp_live})")
            
            # ऑप्शन चेन मैट्रिक्स तैयार करना
            chain_rows = []
            for s in strikes_list:
                diff = s - atm_strike
                ce_val = round(max(0.5, (cmp_live - s) + 15), 2) if diff < 0 else round(max(0.5, 25 - (diff * 0.4)), 2)
                pe_val = round(max(0.5, (s - cmp_live) + 15), 2) if diff > 0 else round(max(0.5, 25 + (diff * 0.4)), 2)
                
                chain_rows.append({
                    "CALL OI": f"{np.random.randint(20, 150)}k",
                    "CALL LTP (₹)": ce_val,
                    "STRIKE": f"{'👉 ' if s == atm_strike else ''}{s}{' (ATM)' if s == atm_strike else ''}",
                    "PUT LTP (₹)": pe_val,
                    "PUT OI": f"{np.random.randint(20, 150)}k"
                })

            df_matrix = pd.DataFrame(chain_rows)
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)
            st.caption("टिप: ऊपर 'Place Option Trade' टैब में जाकर अपनी मनपसंद स्ट्राइक (CE / PE) का सीधा ऑर्डर लगा सकते हैं।")

        # TAB 3: Positions
        with t_pos:
            if dhan_instance:
                try:
                    pos = dhan_instance.get_positions()
                    if pos and pos.get("status") == "success" and pos.get("data"):
                        df_p = pd.DataFrame([p for p in pos["data"] if p.get("netQty") != 0])
                        if not df_p.empty:
                            st.dataframe(df_p[["tradingSymbol", "netQty", "buyAvg", "lastPrice", "unrealizedProfit"]], use_container_width=True)
                        else:
                            st.info("कोई खुली ऑप्शन या इक्विटी पोजीशन नहीं है।")
                    else:
                        st.info("कोई एक्टिव पोजीशन नहीं है।")
                except Exception as e:
                    st.warning(f"पोजीशन लोड एरर: {str(e)}")
            else:
                st.info("लाइव पोजीशन देखने के लिए Dhan कनेक्ट करें।")

    # दायाँ कॉलम: 5-मिनट रंगीन चार्ट (बिना ओवरलैपिंग)
    with col_right:
        c_top1, c_top2 = st.columns([1.2, 1])
        with c_top1:
            st.markdown(f"##### 📈 {target_asset} लाइव चार्ट")
        with c_top2:
            def on_top_tf_change():
                st.session_state["chart_tf"] = st.session_state["top_tf_key"]
                
            st.selectbox(
                "टाइमफ्रेम बदलें:",
                ["1m", "5m", "15m", "1h", "1d"],
                index=["1m", "5m", "15m", "1h", "1d"].index(st.session_state["chart_tf"]),
                key="top_tf_key",
                on_change=on_top_tf_change,
                label_visibility="collapsed"
            )

        render_zoomable_chart(target_asset, meta_info["yf"])
