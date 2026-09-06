# ================= 3. Dhan API Connection (Sidebar) =================
with st.sidebar:
  st.header("⚡ Dhan API Setup")
  st.caption("Enter your 24-hour Dhan access token:")
  dhan_client_id = st.text_input(
      "Dhan Client ID",
      value=st.session_state.get("dhan_client_id", ""),
      type="password",
  )
  dhan_token = st.text_input(
      "Dhan Access Token",
      value=st.session_state.get("dhan_token", ""),
      type="password",
  )

  dhan_instance = None
  if dhan_client_id and dhan_token and DHAN_AVAILABLE:
    clean_id = str(dhan_client_id).strip()
    clean_tok = str(dhan_token).strip()
    try:
      dhan_instance = dhanhq(clean_id, clean_tok)
      # टेस्ट कॉल: Dhan प्रोफाइल फेच करके जांचना
      profile_check = dhan_instance.get_fund_limits()
      if profile_check and profile_check.get("status") == "success":
        st.session_state["dhan_client_id"] = clean_id
        st.session_state["dhan_token"] = clean_tok
        st.success("🟢 Dhan API Live Connected")
      else:
        err_msg = (
            profile_check.get("remarks")
            if profile_check
            else "Invalid Token / ID"
        )
        st.error(f"Dhan Auth Failed: {err_msg}")
        dhan_instance = None
    except Exception as e:
      st.error(f"Connection Exception: {str(e)}")
      dhan_instance = None
  else:
    st.info("⚪ Yahoo Finance Backup Active")
