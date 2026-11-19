"""
LLM Client Provider for Interview Generation & Evaluation.
Supports:
1. Groq (qwen/qwen3.8-27b, openai/gpt-oss-120b, openai/gpt-oss-20b)
2. Google Gemini (gemini-2.5-flash, gemini-flash-latest)
3. OpenAI (gpt-4o-mini, gpt-4o)
Includes automatic model failover, robust JSON parsing, and secret resolution.
"""
import os
import json
import re
import time
from typing import Dict, Any, Optional

_LLM_CIRCUIT_OPEN_UNTIL: float = 0.0

def get_secret(name: str) -> Optional[str]:
    """Retrieve secret from Streamlit secrets, environment, or .streamlit/secrets.toml."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass

    env_val = os.getenv(name)
    if env_val:
        return env_val

    # Direct fallback to local .streamlit/secrets.toml
    try:
        import toml
        toml_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
        if os.path.exists(toml_path):
            data = toml.load(toml_path)
            if name in data:
                return data[name]
    except Exception:
        pass

    return None

def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Strip markdown code block tags and parse JSON."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
    return json.loads(cleaned)

def call_llm(prompt: str, system_prompt: Optional[str] = None, json_mode: bool = False) -> str:
    """
    Invoke available LLM with auto-failover:
    Priority 1: Groq active models ('llama-3.3-70b-versatile', 'openai/gpt-oss-120b', 'openai/gpt-oss-20b')
    Priority 2: Google Gemini ('gemini-2.5-flash', 'gemini-flash-latest')
    Priority 3: OpenAI ('gpt-4o-mini')
    """
    global _LLM_CIRCUIT_OPEN_UNTIL
    if time.time() < _LLM_CIRCUIT_OPEN_UNTIL:
        raise RuntimeError("LLM circuit breaker active after recent connectivity failure; using deterministic fallback.")

    groq_key = get_secret("GROQ_API_KEY") or get_secret("GROQ_KEY")
    gemini_key = get_secret("GOOGLE_API_KEY") or get_secret("GEMINI_KEY")
    openai_key = get_secret("OPENAI_API_KEY") or get_secret("OPENAI_KEY")

    last_error = None

    # 1. Try Groq with active models
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key, timeout=8.0, max_retries=0)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Try active models in order
            candidate_models = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            for m in candidate_models:
                try:
                    kwargs = {
                        "model": m,
                        "messages": messages,
                        "temperature": 0.2,
                    }
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}
                    response = client.chat.completions.create(**kwargs)
                    return response.choices[0].message.content
                except Exception as model_err:
                    last_error = model_err
                    continue
        except Exception as e:
            last_error = e

    # 2. Try Gemini with active models
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            for m_name in ["gemini-2.5-flash", "gemini-flash-latest"]:
                try:
                    model = genai.GenerativeModel(m_name)
                    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                    response = model.generate_content(full_prompt, request_options={"timeout": 8.0})
                    if response and response.text:
                        return response.text
                except Exception as gem_err:
                    last_error = gem_err
                    continue
        except Exception as e:
            last_error = e

    # 3. Try OpenAI
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key, timeout=8.0, max_retries=0)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.2
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e

    _LLM_CIRCUIT_OPEN_UNTIL = time.time() + 60.0
    raise RuntimeError(
        f"All configured LLM providers failed. Last encountered error: {str(last_error)}. "
        "Please check your API keys in .streamlit/secrets.toml."
    )
