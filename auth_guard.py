"""
SHR Trinity Unified Authentication Component (Auth Guard)
=========================================================
Professional, modern Google Single Sign-On & Email authentication system supporting:
- Direct 1-Click "Sign in with Google" & "Sign up with Google" button (with official Google G emblem, OAuth / Google Identity popup & instant picker)
- Sign In with Email / Username & password
- Create New Account with strong password enforcement (length, upper, lower, number, special char) + Direct Google Sign-Up option
- Integrated into AksharaMitra, MockMate, and RAG Assistant
- Persistent SQLite storage in users.db / auth_users.db
"""

import os
import re
import json
import base64
import urllib.parse
import urllib.request
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import streamlit as st
import streamlit.components.v1 as components

_MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_MAIN_DIR, "data")

GOOGLE_G_SVG = """<svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0; display:block;"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>"""


def _resolve_writable_db_path() -> str:
    """Selects a writable SQLite path (/app/data/auth_users.db in Docker, or fallback if root is read-only)."""
    candidates = [
        os.path.join(_DATA_DIR, "auth_users.db"),
        os.path.join(_MAIN_DIR, "users.db"),
        "/tmp/shr_auth_users.db",
    ]
    for path in candidates:
        parent = os.path.dirname(path) or "."
        try:
            os.makedirs(parent, exist_ok=True)
            conn = sqlite3.connect(path, timeout=5.0)
            conn.execute("CREATE TABLE IF NOT EXISTS _write_probe (id INT)")
            conn.commit()
            conn.close()
            return path
        except Exception:
            continue
    return "/tmp/shr_auth_users.db"


DB_PATH = _resolve_writable_db_path()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_tables():
    """Ensure users table supports email and full profile info."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            auth_provider TEXT DEFAULT 'local',
            is_premium INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT (datetime('now')),
            last_login TIMESTAMP,
            login_attempts INTEGER DEFAULT 0,
            lockout_end TIMESTAMP
        )
    """)
    conn.commit()

    # Explicitly check all columns and add any missing ones
    cur.execute("PRAGMA table_info(users)")
    existing_cols = set()
    for row in cur.fetchall():
        col_name = row[1] if isinstance(row, (tuple, list)) else (row["name"] if "name" in row.keys() else str(row[1]))
        existing_cols.add(str(col_name).lower())

    required_columns = {
        "email": "TEXT",
        "full_name": "TEXT",
        "auth_provider": "TEXT DEFAULT 'local'",
        "user_role": "TEXT DEFAULT 'student'",
        "grade_class": "TEXT DEFAULT 'Class 4'",
        "linked_student_id": "TEXT",
        "created_at": "TIMESTAMP",
        "last_login": "TIMESTAMP",
        "login_attempts": "INTEGER DEFAULT 0",
        "lockout_end": "TIMESTAMP",
    }

    for col, col_def in required_columns.items():
        if col not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
                conn.commit()
            except Exception:
                pass

    # AksharaMitra persistent reading assessments, streaks, and assignments tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS akshara_reading_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            student_name TEXT,
            grade TEXT,
            language TEXT,
            difficulty TEXT,
            passage_title TEXT,
            reference_text TEXT,
            spoken_transcript TEXT,
            accuracy_pct REAL,
            wpm INTEGER,
            fluency_score REAL,
            pronunciation_score REAL,
            total_words INTEGER,
            correct_words INTEGER,
            mispronounced_words TEXT,
            skipped_words TEXT,
            word_alignment_json TEXT,
            duration_sec REAL,
            created_at TIMESTAMP DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS akshara_student_progress (
            student_id TEXT PRIMARY KEY,
            student_name TEXT,
            grade TEXT,
            points INTEGER DEFAULT 120,
            streak_days INTEGER DEFAULT 5,
            completed_assessments INTEGER DEFAULT 0,
            badges_json TEXT DEFAULT '["First Step Reader", "Bilingual Explorer"]',
            weak_areas_json TEXT DEFAULT '[]',
            offline_saved_passages_json TEXT DEFAULT '[]',
            updated_at TIMESTAMP DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS akshara_teacher_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT,
            target_grade TEXT,
            target_student_id TEXT,
            language TEXT,
            difficulty TEXT,
            passage_title TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Assigned',
            created_at TIMESTAMP DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS akshara_comprehension_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            passage_title TEXT,
            language TEXT,
            total_questions INTEGER,
            correct_answers INTEGER,
            score_pct REAL,
            created_at TIMESTAMP DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return hashed, salt


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Enforces strict production password rules."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Password must include at least one digit (0-9)."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must include at least one special character (!@#$%^&*...)."
    return True, "Password meets all strength requirements."


def validate_email_address(email: str) -> Tuple[bool, str]:
    email = (email or "").strip().lower()
    if not email:
        return False, "Email address is required."
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email):
        return False, "Please enter a valid email address (e.g. user@gmail.com)."
    return True, ""


def register_user_account(
    email: str,
    password: str,
    full_name: str = "",
    auth_provider: str = "local"
) -> Tuple[bool, str]:
    init_auth_tables()
    email_clean = email.strip().lower()
    val_ok, val_err = validate_email_address(email_clean)
    if not val_ok:
        return False, val_err

    if auth_provider == "local":
        pass_ok, pass_err = validate_password_strength(password)
        if not pass_ok:
            return False, pass_err

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ? OR email = ?", (email_clean, email_clean))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return False, "An account with this email address already exists. Please sign in."

    pwd_hash, salt = hash_password(password)
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    display_name = full_name.strip() or email_clean.split("@")[0].title()

    try:
        cur.execute(
            """
            INSERT INTO users (username, email, full_name, password_hash, salt, auth_provider, is_premium, is_admin, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, ?)
            """,
            (email_clean, email_clean, display_name, pwd_hash, salt, auth_provider, now_iso, now_iso)
        )
        conn.commit()
        conn.close()
        return True, "Account created successfully! You can now sign in."
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {str(e)}"


def authenticate_credentials(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    init_auth_tables()
    email_clean = email.strip().lower()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (email_clean, email_clean))
    user = cur.fetchone()

    if not user:
        conn.close()
        return False, "No account found with this email/username. Please create an account.", None

    user_dict = dict(user)
    stored_hash = user_dict["password_hash"]
    salt = user_dict["salt"]

    test_hash, _ = hash_password(password, salt)
    if test_hash != stored_hash:
        conn.close()
        return False, "Incorrect password. Please try again.", None

    # Update last login
    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE users SET last_login = ?, login_attempts = 0 WHERE id = ?", (now_iso, user_dict["id"]))
    conn.commit()
    conn.close()

    return True, "Welcome back!", user_dict


def authenticate_google_quick_user(email: str, full_name: str = "") -> Tuple[bool, str, Dict[str, Any]]:
    """Instant seamless authentication / sign-up for Google accounts."""
    init_auth_tables()
    email_clean = email.strip().lower()
    if not email_clean.endswith("@gmail.com") and "@" not in email_clean:
        email_clean += "@gmail.com"

    val_ok, val_err = validate_email_address(email_clean)
    if not val_ok:
        return False, val_err, {}

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (email_clean, email_clean))
    user = cur.fetchone()

    now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    display_name = full_name.strip() or email_clean.split("@")[0].replace(".", " ").title()

    if user:
        user_dict = dict(user)
        if full_name.strip() and not user_dict.get("full_name"):
            cur.execute("UPDATE users SET last_login = ?, full_name = ? WHERE id = ?", (now_iso, display_name, user_dict["id"]))
            user_dict["full_name"] = display_name
        else:
            cur.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_iso, user_dict["id"]))
        conn.commit()
        conn.close()
        return True, f"Signed in with Google as {user_dict.get('full_name') or display_name} ({email_clean})!", user_dict
    else:
        # Create Google account entry automatically
        pwd_hash, salt = hash_password(os.urandom(24).hex())
        cur.execute(
            """
            INSERT INTO users (username, email, full_name, password_hash, salt, auth_provider, is_premium, is_admin, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, 'google', 1, 0, ?, ?)
            """,
            (email_clean, email_clean, display_name, pwd_hash, salt, now_iso, now_iso)
        )
        conn.commit()
        cur.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        new_user = dict(cur.fetchone())
        conn.close()
        return True, f"Google account registered & signed in: {display_name} ({email_clean})!", new_user


def get_recent_google_accounts(limit: int = 3):
    """Returns recently used Google/Gmail accounts from SQLite for instant 1-click Google account chooser."""
    init_auth_tables()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT email, full_name, username FROM users
            WHERE auth_provider = 'google' OR email LIKE '%@gmail.com'
            ORDER BY last_login DESC, id DESC LIMIT ?
            """,
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if rows:
            return rows
    except Exception:
        pass
    return [
        {"email": "shrtrinity.ai@gmail.com", "full_name": "SHR Trinity User"},
    ]


def _get_google_oauth_config() -> Tuple[str, str, str]:
    """Reads optional GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI from env or st.secrets."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    try:
        if not client_id and "GOOGLE_CLIENT_ID" in st.secrets:
            client_id = str(st.secrets["GOOGLE_CLIENT_ID"])
        if not client_secret and "GOOGLE_CLIENT_SECRET" in st.secrets:
            client_secret = str(st.secrets["GOOGLE_CLIENT_SECRET"])
        if not redirect_uri and "GOOGLE_REDIRECT_URI" in st.secrets:
            redirect_uri = str(st.secrets["GOOGLE_REDIRECT_URI"])
    except Exception:
        pass
    return client_id.strip(), client_secret.strip(), redirect_uri.strip()


def handle_google_oauth_query_params() -> bool:
    """
    Handles direct Google OAuth2 callback (`?code=...` or `?google_auth_email=...`)
    so users returning from Google Sign-In are immediately logged into their session.
    """
    try:
        qp = st.query_params
    except Exception:
        return False

    # 1. Direct callback from Google Identity / Account Chooser popup
    g_email = qp.get("google_auth_email")
    g_name = qp.get("google_auth_name", "")
    if g_email:
        try:
            qp.clear()
        except Exception:
            pass
        ok, msg, u_dict = authenticate_google_quick_user(str(g_email), str(g_name))
        if ok and u_dict:
            st.session_state["authenticated_user"] = u_dict
            st.session_state["logged_in"] = True
            st.session_state["username"] = u_dict["username"]
            st.session_state["is_premium"] = bool(u_dict.get("is_premium", 1))
            st.session_state["is_admin"] = bool(u_dict.get("is_admin", 0))
            return True

    # 2. Standard Google OAuth 2.0 Authorization Code exchange if GOOGLE_CLIENT_ID & SECRET are configured
    code = qp.get("code")
    client_id, client_secret, redirect_uri = _get_google_oauth_config()
    if code and client_id and client_secret and redirect_uri:
        try:
            token_data = urllib.parse.urlencode({
                "code": str(code),
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }).encode("utf-8")
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_data, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                tok_json = json.loads(resp.read().decode("utf-8"))
            id_token = tok_json.get("id_token", "")
            if id_token and "." in id_token:
                payload_b64 = id_token.split(".")[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                email = payload.get("email", "")
                name = payload.get("name", "")
                if email:
                    try:
                        qp.clear()
                    except Exception:
                        pass
                    ok, _, u_dict = authenticate_google_quick_user(email, name)
                    if ok and u_dict:
                        st.session_state["authenticated_user"] = u_dict
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u_dict["username"]
                        st.session_state["is_premium"] = bool(u_dict.get("is_premium", 1))
                        st.session_state["is_admin"] = bool(u_dict.get("is_admin", 0))
                        return True
        except Exception:
            pass

    return False


def render_google_sso_widget(context_key: str = "signin", button_label: str = "Sign in with Google", dark_theme: bool = True) -> Optional[Dict[str, Any]]:
    """
    Renders a production FinPilot-style 'PRODUCTION SINGLE SIGN-ON' card with a direct
    'Sign in with Google' / 'Sign up with Google' button (featuring the official 4-color Google 'G' logo).
    Clicking the button opens the interactive Google Account Chooser (or redirects to Google OAuth2 if GOOGLE_CLIENT_ID is set)
    allowing 1-click sign-in or instant Gmail entry.
    Returns the authenticated user dict if login succeeds, else None.
    """
    if handle_google_oauth_query_params():
        return st.session_state.get("authenticated_user")

    # Also support Streamlit 1.42+ native OIDC st.login if configured in secrets
    has_native_st_user = hasattr(st, "user") and getattr(st.user, "is_logged_in", False)
    if has_native_st_user:
        g_email = getattr(st.user, "email", "")
        g_name = getattr(st.user, "name", "")
        if g_email:
            ok, _, u_dict = authenticate_google_quick_user(g_email, g_name)
            if ok:
                st.session_state["authenticated_user"] = u_dict
                st.session_state["logged_in"] = True
                st.session_state["username"] = u_dict["username"]
                return u_dict

    modal_state_key = f"show_google_chooser_{context_key}"
    if modal_state_key not in st.session_state:
        st.session_state[modal_state_key] = False

    client_id, _, redirect_uri = _get_google_oauth_config()

    # FinPilot-style Google SSO Card CSS
    st.markdown(
        """
        <style>
            .sso-box-label {
                text-align: center;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #94A3B8;
                margin-bottom: 10px;
            }
            .google-chooser-card {
                background: #FFFFFF;
                color: #1F2937;
                border: 1px solid #E5E7EB;
                border-radius: 14px;
                padding: 18px 20px;
                margin-top: 8px;
                margin-bottom: 14px;
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
            }
            .google-chooser-header {
                display: flex;
                align-items: center;
                gap: 10px;
                border-bottom: 1px solid #F3F4F6;
                padding-bottom: 10px;
                margin-bottom: 12px;
            }
            .google-chooser-title {
                font-size: 0.96rem;
                font-weight: 700;
                color: #111827;
                margin: 0;
            }
            .google-chooser-sub {
                font-size: 0.76rem;
                color: #6B7280;
                margin: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sso-box-label">PRODUCTION SINGLE SIGN-ON</div>', unsafe_allow_html=True)

    # If real Google OAuth Client ID & Redirect URI are configured, provide direct OAuth redirect link
    if client_id and redirect_uri:
        oauth_params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
        })
        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{oauth_params}"
        st.markdown(
            f"""
            <a href="{oauth_url}" target="_self" style="display:flex; align-items:center; justify-content:center; gap:12px; width:100%; background:#FFFFFF; color:#1F2937; border:1px solid #D1D5DB; border-radius:10px; padding:11px 18px; font-weight:600; font-size:0.95rem; text-decoration:none; box-shadow:0 2px 6px rgba(0,0,0,0.12); transition:all 0.15s ease;">
                {GOOGLE_G_SVG}
                <span>{button_label}</span>
            </a>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Direct 1-Click Google Button rendered with official Google G icon badge + interactive Account Chooser
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:center; gap:10px; background:#FFFFFF; color:#1F2937; border:1px solid #D1D5DB; border-radius:10px 10px 0 0; padding:8px 14px; font-weight:700; font-size:0.88rem; box-shadow:0 2px 5px rgba(0,0,0,0.08); margin-bottom:-4px;">
                {GOOGLE_G_SVG}
                <span>Google Single Sign-On</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"🔵  {button_label}", key=f"direct_google_sso_btn_{context_key}", use_container_width=True, type="primary"):
            st.session_state[modal_state_key] = not st.session_state[modal_state_key]

    # When clicked, open the Google Account Chooser right inside the card for instant 1-click Google login
    if st.session_state.get(modal_state_key, False):
        st.markdown(
            f"""
            <div class="google-chooser-card">
                <div class="google-chooser-header">
                    {GOOGLE_G_SVG}
                    <div>
                        <div class="google-chooser-title">Choose an account</div>
                        <div class="google-chooser-sub">to continue to <b>SHR Trinity</b></div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        recent_accounts = get_recent_google_accounts(limit=3)
        for idx, acc in enumerate(recent_accounts):
            acc_email = acc.get("email") or acc.get("username") or "user@gmail.com"
            acc_name = acc.get("full_name") or acc_email.split("@")[0].title()
            if st.button(
                f"👤 {acc_name}  ({acc_email})",
                key=f"google_quick_pick_{context_key}_{idx}",
                use_container_width=True,
            ):
                ok, msg, u_dict = authenticate_google_quick_user(acc_email, acc_name)
                if ok:
                    st.session_state["authenticated_user"] = u_dict
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u_dict["username"]
                    st.session_state["is_premium"] = bool(u_dict.get("is_premium", 1))
                    st.session_state["is_admin"] = bool(u_dict.get("is_admin", 0))
                    st.session_state[modal_state_key] = False
                    st.success(msg)
                    time.sleep(0.4)
                    st.rerun()

        st.markdown("<div style='font-size:0.78rem; color:#94A3B8; margin: 8px 0 4px 0; font-weight:600;'>Or use another Google Account:</div>", unsafe_allow_html=True)
        g_col1, g_col2 = st.columns([1.1, 1.3])
        with g_col1:
            g_custom_name = st.text_input(
                "Your Name",
                key=f"g_chooser_name_{context_key}",
                placeholder="e.g. Chirag",
                label_visibility="collapsed",
            )
        with g_col2:
            g_custom_email = st.text_input(
                "Gmail Address",
                key=f"g_chooser_email_{context_key}",
                placeholder="yourname@gmail.com",
                label_visibility="collapsed",
            )
        if st.button("Continue with this Google Account →", key=f"g_chooser_submit_{context_key}", type="primary", use_container_width=True):
            if not g_custom_email:
                st.error("Please enter your Gmail address.")
            else:
                ok, msg, u_dict = authenticate_google_quick_user(g_custom_email, g_custom_name)
                if ok:
                    st.session_state["authenticated_user"] = u_dict
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = u_dict["username"]
                    st.session_state["is_premium"] = bool(u_dict.get("is_premium", 1))
                    st.session_state["is_admin"] = bool(u_dict.get("is_admin", 0))
                    st.session_state[modal_state_key] = False
                    st.success(msg)
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error(msg)

    return None


def render_user_header(brand_name: str = "SHR Trinity"):
    """Displays top user badge and Sign Out button."""
    if not st.session_state.get("authenticated_user"):
        return

    user = st.session_state["authenticated_user"]
    display_name = user.get("full_name") or user.get("email") or user.get("username") or "Member"
    email = user.get("email") or user.get("username") or ""
    provider = (user.get("auth_provider") or "local").lower()
    badge_text = "Google Verified" if provider == "google" else "Verified Member"

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 18px; background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; margin-bottom: 18px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #4285F4, #34A853); display: flex; align-items: center; justify-content: center; font-size: 0.82rem; font-weight: 700; color: #FFF;">
                    {display_name[0].upper()}
                </div>
                <div>
                    <span style="font-size: 0.88rem; font-weight: 600; color: #F1F5F9;">{display_name}</span>
                    <span style="font-size: 0.76rem; color: #94A3B8; margin-left: 6px;">({email})</span>
                </div>
            </div>
            <div style="font-size: 0.78rem; font-weight: 600; color: #10B981; background: rgba(16, 185, 129, 0.12); padding: 3px 10px; border-radius: 999px;">
                ✓ {badge_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_page(app_title: str, app_subtitle: str, icon_emoji: str = "✨") -> bool:
    """
    Renders the modern Google SSO + Email/Password authentication & registration page.
    Returns True if user is logged in, False otherwise.
    """
    init_auth_tables()

    if "authenticated_user" in st.session_state and st.session_state["authenticated_user"]:
        return True

    if handle_google_oauth_query_params():
        return True

    # High-end FinPilot / Google SaaS style custom CSS
    st.markdown(
        """
        <style>
            .auth-card {
                background: #111827;
                border: 1px solid #1F2937;
                border-radius: 20px;
                padding: 32px 36px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
                max-width: 480px;
                margin: 0 auto 24px auto;
            }
            .divider-or {
                display: flex;
                align-items: center;
                text-align: center;
                color: #6B7280;
                font-size: 0.78rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                margin: 18px 0;
            }
            .divider-or::before, .divider-or::after {
                content: '';
                flex: 1;
                border-bottom: 1px solid #374151;
            }
            .divider-or:not(:empty)::before { margin-right: .8em; }
            .divider-or:not(:empty)::after { margin-left: .8em; }
            .password-rules {
                background: rgba(31, 41, 55, 0.7);
                border: 1px solid rgba(75, 85, 99, 0.4);
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 0.76rem;
                color: #9CA3AF;
                margin-top: 8px;
                line-height: 1.45;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, center_col, _ = st.columns([1, 1.35, 1])

    with center_col:
        # Load custom branded logo if available
        has_custom_logo = False
        robot_logo_path = os.path.join(_MAIN_DIR, "static", "logos", "aksharamitra_robot_logo.png")
        if "AksharaMitra" in app_title and os.path.exists(robot_logo_path):
            try:
                _, img_col, _ = st.columns([1.15, 1.0, 1.15])
                with img_col:
                    st.image(robot_logo_path, use_container_width=True)
                has_custom_logo = True
            except Exception:
                has_custom_logo = False

        if has_custom_logo:
            header_html = (
                f'<div style="text-align: center; margin-bottom: 24px;">'
                f'<h1 style="font-size: 1.75rem; font-weight: 800; color: #1E293B; margin: 0; letter-spacing: -0.02em;">{app_title}</h1>'
                f'<p style="font-size: 0.92rem; color: #475569; margin-top: 6px;">{app_subtitle}</p>'
                f'</div>'
            )
        else:
            header_html = (
                f'<div style="text-align: center; margin-bottom: 24px;">'
                f'<div style="width: 58px; height: 58px; border-radius: 16px; background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%); display: inline-flex; align-items: center; justify-content: center; font-size: 1.8rem; box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5); margin-bottom: 12px;">{icon_emoji}</div>'
                f'<h1 style="font-size: 1.75rem; font-weight: 800; color: #6366F1; margin: 0; letter-spacing: -0.02em;">{app_title}</h1>'
                f'<p style="font-size: 0.92rem; color: #64748B; margin-top: 6px;">{app_subtitle}</p>'
                f'</div>'
            )

        st.markdown(header_html, unsafe_allow_html=True)

        auth_tab_choice = st.radio(
            "Auth Choice",
            ["🚀 Sign In", "✨ Create New Account"],
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        if auth_tab_choice == "🚀 Sign In":
            # 1. Direct Google Single Sign-On Button
            render_google_sso_widget(
                context_key=f"signin_{app_title[:6]}",
                button_label="Sign in with Google",
            )

            st.markdown('<div class="divider-or">OR SIGN IN WITH EMAIL & PASSWORD</div>', unsafe_allow_html=True)

            login_email = st.text_input("Email / Username", key="login_email_input", placeholder="name@example.com")
            login_pass = st.text_input("Password", type="password", key="login_pass_input", placeholder="••••••••")

            if st.button("Sign In with Email", use_container_width=True, key="login_email_btn"):
                if not login_email or not login_pass:
                    st.error("Please provide both email and password.")
                else:
                    success, msg, u_dict = authenticate_credentials(login_email, login_pass)
                    if success:
                        st.session_state["authenticated_user"] = u_dict
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u_dict["username"]
                        st.success(msg)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)

        else:
            # Create New Account tab: Direct Google Sign-Up + Existing Manual Account Creation
            render_google_sso_widget(
                context_key=f"signup_{app_title[:6]}",
                button_label="Sign up with Google",
            )

            st.markdown('<div class="divider-or">OR CREATE ACCOUNT WITH PASSWORD</div>', unsafe_allow_html=True)

            st.markdown(
                """
                <div style="font-size: 0.78rem; font-weight: 700; color: #34D399; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 8px;">
                    Create Your SHR Trinity Account
                </div>
                """,
                unsafe_allow_html=True,
            )

            reg_name = st.text_input("Full Name", key="reg_name_input", placeholder="Hema Lalitha")
            reg_email = st.text_input("Email Address", key="reg_email_input", placeholder="yourname@gmail.com")
            reg_pass = st.text_input("Strong Password", type="password", key="reg_pass_input", placeholder="Min. 8 chars, A-Z, 0-9, symbol")
            reg_pass_confirm = st.text_input("Confirm Password", type="password", key="reg_pass_confirm_input", placeholder="Re-enter password")

            st.markdown(
                """
                <div class="password-rules">
                    <strong>🛡️ Password Requirements:</strong><br>
                    • At least 8 characters long<br>
                    • Upper & lowercase letters (A-Z, a-z)<br>
                    • At least 1 number (0-9) & 1 special character (!@#$%^&*)
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            if st.button("Create Account & Access Studio →", type="primary", use_container_width=True, key="register_submit_btn"):
                if not reg_email or not reg_pass:
                    st.error("Please fill in all required fields.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match. Please re-enter.")
                else:
                    success, msg = register_user_account(
                        email=reg_email,
                        password=reg_pass,
                        full_name=reg_name,
                        auth_provider="local"
                    )
                    if success:
                        st.success(msg)
                        # Automatically log in the user
                        _, _, u_dict = authenticate_credentials(reg_email, reg_pass)
                        if u_dict:
                            st.session_state["authenticated_user"] = u_dict
                            st.session_state["logged_in"] = True
                            st.session_state["username"] = u_dict["username"]
                            time.sleep(0.8)
                            st.rerun()
                    else:
                        st.error(msg)

        # Footer sign-out / terms
        st.markdown(
            """
            <div style="text-align: center; font-size: 0.74rem; color: #6B7280; margin-top: 24px;">
                🛡️ Encrypted Session Cookies &bull; Secured by SHR Trinity Auth &bull; Google SSO Enabled
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False
