"""
Every Child Reads – Telugu AI Reading Assessment Platform
Department of School Education, Government of Andhra Pradesh
Multi-page Entrypoint
"""
import streamlit as st
from telugu_reading_app import render_main_app

# The page config in Streamlit multi-page can be set here if not already set
try:
    st.set_page_config(
        page_title="Every Child Reads | ప్రతి బిడ్డా చదవాలి",
        page_icon="📖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception:
    pass

if __name__ == "__main__":
    render_main_app()

