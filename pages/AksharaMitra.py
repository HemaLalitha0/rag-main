"""
AksharaMitra (అక్షరమిత్ర) – AI-Powered Bilingual Reading Intelligence & Personalized Learning Platform
An Education Technology Innovation by SHR Trinity
Multi-page Entrypoint
"""
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

