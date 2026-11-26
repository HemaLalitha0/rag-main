"""
AksharaMitra (అక్షరమిత్ర) – AI-Powered Bilingual Reading Intelligence & Personalized Learning Platform
An Education Technology Innovation by SHR Trinity
Multi-page Entrypoint with Gmail & Email Auth Guard
"""
import os
import sys

# Ensure project root (/app) is on sys.path when pages/AksharaMitra.py is run directly
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import streamlit as st

# Configure browser tab title and icon for AksharaMitra
try:
    st.set_page_config(
        page_title="AksharaMitra | అక్షరమిత్ర – SHR Trinity",
        page_icon="📖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
except Exception:
    pass

import importlib
import auth_guard
importlib.reload(auth_guard)
from auth_guard import render_auth_page, render_user_header
from telugu_reading_app import render_main_app

# Check authentication gate
is_logged_in = render_auth_page(
    app_title="AksharaMitra (అక్షరమిత్ర)",
    app_subtitle="Bilingual Telugu & English AI Reading Platform. Sign in with your Gmail or create an account to begin.",
    icon_emoji="📖",
)

if is_logged_in:
    u_col1, u_col2 = st.columns([5, 1])
    with u_col1:
        render_user_header("AksharaMitra")
    with u_col2:
        if st.button("Sign Out", key="aksharamitra_sign_out_btn", use_container_width=True):
            st.session_state["authenticated_user"] = None
            st.session_state["logged_in"] = False
            st.rerun()

    render_main_app()
