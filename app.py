# app.py
import sys
if "torchvision" not in sys.modules:
    sys.modules["torchvision"] = None

import streamlit as st

# Set up the main app
st.set_page_config(
    page_title="RAG Assistant", 
    page_icon="📚",
    layout="wide"
)

# Show the login page by default
st.switch_page("pages/login.py")
