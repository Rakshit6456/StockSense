"""Streamlit entry point (Person 3): login + navigation. Pages live in pages/."""
import streamlit as st

from backend.auth import authenticate, ensure_default_admin

st.set_page_config(page_title="Smart Inventory", layout="wide")
ensure_default_admin()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("Smart Inventory Management System")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            user = authenticate(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password")
else:
    st.sidebar.write(f"Logged in as **{st.session_state.user['username']}** "
                     f"({st.session_state.user['role']})")
    if st.sidebar.button("Log out"):
        st.session_state.user = None
        st.rerun()
    st.title("Dashboard")
    st.info("TODO (Person 3): dashboard cards, alerts panel. "
            "Use backend.inventory.dashboard_summary().")
