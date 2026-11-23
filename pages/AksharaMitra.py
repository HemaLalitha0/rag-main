"""
AksharaMitra (అక్షరమిత్ర) – AI-Powered Bilingual Reading Intelligence & Personalized Learning Platform
An Education Technology Innovation by SHR Trinity
Multi-page Entrypoint
"""
import os
import sys

# Ensure project root (/app) is on sys.path when pages/AksharaMitra.py is run directly
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import streamlit as st
from telugu_reading_app import render_main_app

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

if __name__ == "__main__":
    render_main_app()

