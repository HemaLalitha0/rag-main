"""
MockMate (SHR Trinity) - Production Entry Point with Modern Gmail & Email Auth Guard
===================================================================================
Dedicated entry point for MockMate service container.
"""

import sys
import os

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import streamlit as st

st.set_page_config(
    page_title="MockMate — AI Interview Studio | SHR Trinity",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import importlib
import auth_guard
importlib.reload(auth_guard)
from auth_guard import render_auth_page, render_user_header

# Check authentication gate
is_logged_in = render_auth_page(
    app_title="MockMate AI Studio",
    app_subtitle="Sign in with your Gmail or create an account to start your AI mock interview.",
    icon_emoji="🎙️",
)

if is_logged_in:
    # Render user profile bar with Sign Out button
    u_col1, u_col2 = st.columns([5, 1])
    with u_col1:
        render_user_header("MockMate")
    with u_col2:
        if st.button("Sign Out", key="mockmate_sign_out_btn", use_container_width=True):
            st.session_state["authenticated_user"] = None
            st.session_state["logged_in"] = False
            st.rerun()

    # Delegate to mock interview engine
    import importlib.util
    spec = importlib.util.spec_from_file_location("mock_interview", os.path.join(os.path.dirname(__file__), "mock_interview.py"))
    mock_interview = importlib.util.module_from_spec(spec)
    sys.modules["mock_interview"] = mock_interview
    spec.loader.exec_module(mock_interview)
