import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# DhanHQ Library
try:
    from dhanhq import dhanhq
    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False

# ================= 1. पेज कॉन्फ़िगरेशन =================
st.set_page_config(
    page_title="महादेब स्टॉक रिसर्च",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 2. मास्टर पासवर्ड सुरक्षा गार्ड =================
MASTER_PIN = "990553"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 महादेब स्टॉक रिसर्च")
    st.subheader("सुरक्षित ट्रेडिंग गेटवे")
    st.info("यह एक निजी रिसर्च व ट्रेडिंग पोर्टल है। कृपया एक्सेस के लिए अपना मास्टर पिन दर्ज करें।")
    
    with st.form("login_form"):
        pin_input = st.text_input("मास्टर पिन दर्ज करें:", type="password", placeholder="******")
        submit_btn = st.form_submit_button("लॉगिन करें", use_container_width=True)
        
        if submit_btn:
            if str(pin_input).strip() == MASTER_PIN:
                st.session_state["authenticated"] = True
                st.success("सत्यापन सफल! डैशबोर्ड लोड हो रहा है...")
                st.rerun()
            else:
                st.error("गलत पिन! कृपया पुनः प्रयास करें।")
    st.stop()

# ================= 3. Dhan API कनेक्शन (साइडबार) =================
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

    st.divider()
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("⚡ महादेब स्टॉक रिसर्च")
st.caption("F&O मार्केट इंटेलिजेंस + DhanHQ Advanced Options Trading Terminal")

HEADERS = {"User-Agent": "Mozilla/5.0"}

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

# ================= 4. ट्रेडिंग कंसोल =================
with st.expander("⚡ DHAN ADVANCED OPTIONS & EQUITY TRADING TERMINAL", expanded=True):
    if not dhan_instance:
        st.warning("⚠️ Dhan API Not Connected! Enter Client ID & Access Token in the sidebar to activate live execution.")
    else:
        st.subheader("Order Placement & Position Management")
        tab_order, tab_pos = st.tabs(["🛒 Place Limit / SL Order", "📋 Open Positions (Live P&L)"])

        with tab_order:
            c1, c2, c3 = st.columns(3)
            with c1:
                symbol = st.selectbox("Underlying Asset", list(DHAN_SEC_IDS.keys()))
                quantity = st.number_input("Quantity", min_value=1, value=25, step=1)
            with c2:
                order_side = st.radio("Side", ["BUY", "SELL"], horizontal=True)
                order_type = st.selectbox("Order Type", ["LIMIT", "MARKET"])
            with c3:
                product_type = st.selectbox("Product Type", ["INTRADAY (MIS)", "NORMAL (NRML/CNC)"])
                limit_price = st.number_input("Entry Limit Price (₹)", min_value=0.0, value=100.0, step=0.5)

            st.write("---")
            confirm_box = st.checkbox(f"Confirm {order_side} {quantity} units of {symbol}")
            if st.button("🚀 TRANSMIT ORDER TO NSE", use_container_width=True, type="primary"):
                if confirm_box:
                    try:
                        action = dhan_instance.BUY if order_side == "BUY" else dhan_instance.SELL
                        prod = dhan_instance.INTRA if "INTRADAY" in product_type else dhan_instance.CNC
                        otype = dhan_instance.LIMIT if order_type == "LIMIT" else dhan_instance.MARKET
                        
                        entry_resp = dhan_instance.place_order(
                            security_id=DHAN_SEC_IDS[symbol],
                            exchange_segment=dhan_instance.NSE,
                            transaction_type=action,
                            quantity=int(quantity),
                            order_type=otype,
                            product_type=prod,
                            price=float(limit_price) if order_type == "LIMIT" else 0
                        )
                        if entry_resp.get("status") == "success":
                            st.success(f"Order Placed! ID: {entry_resp.get('data', {}).get('orderId')}")
                        else:
                            st.error(f"Rejected: {entry_resp.get('remarks')}")
                    except Exception as ex:
                        st.error(f"Error: {str(ex)}")
                else:
                    st.warning("Please tick confirmation.")

        with tab_pos:
            if st.button("🔄 Refresh Positions"):
                st.rerun()
            try:
                positions_resp = dhan_instance.get_positions()
                if positions_resp and positions_resp.get("status") == "success" and positions_resp.get("data"):
                    open_pos = [p for p in positions_resp["data"] if p.get("netQty") != 0]
                    if open_pos:
                        st.dataframe(pd.DataFrame(open_pos), use_container_width=True)
                    else:
                        st.info("No open positions active.")
                else:
                    st.info("No open positions.")
            except Exception as e:
                st.warning(f"Error: {str(e)}")
