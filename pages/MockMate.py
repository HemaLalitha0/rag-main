"""
MockMate (SHR Trinity) - Production Entry Point for Mock Interview Studio
========================================================================
Dedicated entry point for MockMate service container.
"""

import sys
import os

_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

import streamlit as st

# Delegate directly to the mock interview page
import importlib.util

spec = importlib.util.spec_from_file_location("mock_interview", os.path.join(os.path.dirname(__file__), "mock_interview.py"))
mock_interview = importlib.util.module_from_spec(spec)
sys.modules["mock_interview"] = mock_interview
spec.loader.exec_module(mock_interview)
