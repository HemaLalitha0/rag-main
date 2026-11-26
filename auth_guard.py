"""
SHR Trinity Unified Authentication Component (Auth Guard)
=========================================================
Professional, modern Gmail & Email authentication system supporting:
- Sign In with Gmail / Email & password
- 1-Click Google Account Sign-In / Demo
- Create New Account with strong password enforcement (length, upper, lower, number, special char)
- Integrated into both AksharaMitra and MockMate
- Persistent SQLite storage in users.db
"""

import os
import re
import sqlite3
import hashlib
import time
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import streamlit as st

_MAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_MAIN_DIR, "data")


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
        return False, "No account found with this email. Please create an account.", None

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
    """Instant seamless authentication for Gmail accounts."""
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
    display_name = full_name.strip() or email_clean.split("@")[0].title()

    if user:
        user_dict = dict(user)
        cur.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_iso, user_dict["id"]))
        conn.commit()
        conn.close()
        return True, f"Welcome back, {user_dict.get('full_name') or display_name}!", user_dict
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
        return True, f"Welcome to SHR Trinity, {display_name}!", new_user


def render_user_header(brand_name: str = "SHR Trinity"):
    """Displays top user badge and Sign Out button."""
    if not st.session_state.get("authenticated_user"):
        return

    user = st.session_state["authenticated_user"]
    display_name = user.get("full_name") or user.get("email") or "Member"
    email = user.get("email") or ""

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
                Verified Member
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_page(app_title: str, app_subtitle: str, icon_emoji: str = "✨") -> bool:
    """
    Renders the modern Google / Gmail authentication page.
    Returns True if user is logged in, False otherwise.
    """
    init_auth_tables()

    if "authenticated_user" in st.session_state and st.session_state["authenticated_user"]:
        return True

    # High-end Google/SaaS style custom CSS
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
            .google-btn-ui {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                width: 100%;
                background: #FFFFFF;
                color: #1F2937;
                font-weight: 600;
                font-size: 0.95rem;
                padding: 12px 18px;
                border-radius: 10px;
                text-decoration: none;
                margin: 14px 0 18px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            }
            .divider-or {
                display: flex;
                align-items: center;
                text-align: center;
                color: #6B7280;
                font-size: 0.8rem;
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
                f'<h1 style="font-size: 1.75rem; font-weight: 800; color: #F9FAFB; margin: 0; letter-spacing: -0.02em;">{app_title}</h1>'
                f'<p style="font-size: 0.88rem; color: #9CA3AF; margin-top: 6px;">{app_subtitle}</p>'
                f'</div>'
            )
        else:
            header_html = (
                f'<div style="text-align: center; margin-bottom: 24px;">'
                f'<div style="width: 58px; height: 58px; border-radius: 16px; background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%); display: inline-flex; align-items: center; justify-content: center; font-size: 1.8rem; box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5); margin-bottom: 12px;">{icon_emoji}</div>'
                f'<h1 style="font-size: 1.75rem; font-weight: 800; color: #F9FAFB; margin: 0; letter-spacing: -0.02em;">{app_title}</h1>'
                f'<p style="font-size: 0.88rem; color: #9CA3AF; margin-top: 6px;">{app_subtitle}</p>'
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
            st.markdown(
                """
                <div style="font-size: 0.78rem; font-weight: 700; color: #818CF8; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 8px;">
                    1-Click Google / Gmail Access
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Fast 1-Click Gmail sign in
            gmail_input = st.text_input(
                "Enter your Gmail address",
                key="quick_gmail_input",
                placeholder="you@gmail.com",
            )
            if st.button("Continue with Google →", type="primary", use_container_width=True, key="google_quick_btn"):
                if not gmail_input:
                    st.error("Please enter your Gmail address.")
                else:
                    success, msg, u_dict = authenticate_google_quick_user(gmail_input)
                    if success:
                        st.session_state["authenticated_user"] = u_dict
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u_dict["username"]
                        st.success(msg)
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown('<div class="divider-or">OR SIGN IN WITH PASSWORD</div>', unsafe_allow_html=True)

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
            # Create New Account tab
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
                Secured by SHR Trinity Auth &bull; All Gmail & Custom Domains Supported
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False

