import streamlit as st
import sqlite3
import hashlib
import os
import time
import base64
import tempfile
from datetime import datetime, timedelta
import re

# CRITICAL: st.set_page_config() MUST be the FIRST Streamlit command
st.set_page_config(
    page_title="RAG Assistant", 
    page_icon="💥",
    layout="centered",
    initial_sidebar_state="expanded"
)

# FIX: Reliable database path that works everywhere
try:
    # Get the directory of the main app (2 levels up from pages/login.py)
    MAIN_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(MAIN_APP_DIR, 'users.db')
except:
    # Fallback to current directory
    DB_PATH = 'users.db'

# Constants
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 300  # 5 minutes in seconds
DEFAULT_ADMIN_CREDENTIALS = ("admin", "admin123")

# Hash password with salt
def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = os.urandom(16).hex()
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest(), salt

# Initialize database with proper error handling
def init_db():
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_premium INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now')),
                last_login TIMESTAMP,
                login_attempts INTEGER DEFAULT 0,
                lockout_end TIMESTAMP
            )
        ''')

        # Create default admin if not exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (DEFAULT_ADMIN_CREDENTIALS[0],))
        if cursor.fetchone() is None:
            password_hash, salt = hash_password(DEFAULT_ADMIN_CREDENTIALS[1])
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt, is_premium, is_admin, created_at) VALUES (?, ?, ?, 1, 1, datetime('now'))",
                (DEFAULT_ADMIN_CREDENTIALS[0], password_hash, salt)
            )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        st.error(f"Database path: {DB_PATH}")
        return False

# Custom CSS for ULTRA-CRAZY Netflix-Themed UI
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800;900&family=Exo+2:wght@400;500;600;700&display=swap');

    :root {
        --netflix-red: #e50914;
        --netflix-dark: #141414;
        --netflix-darker: #0a0a0a;
        --netflix-gray: #222222;
        --text: #ffffff;
        --text-secondary: #b3b3b3;
        --card-bg: #141414;
        --border: #333333;
        --highlight: #ff4757;
        --success: #0be881;
        --warning: #ffcc00;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 var(--netflix-red); }
        70% { box-shadow: 0 0 0 15px rgba(229, 9, 20, 0); }
        100% { box-shadow: 0 0 0 0 rgba(229, 9, 20, 0); }
    }

    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }

    @keyframes shine {
        0% { background-position: -100% 0; }
        100% { background-position: 200% 0; }
    }

    @keyframes explosion {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }

    @keyframes flicker {
        0%, 19%, 21%, 23%, 25%, 54%, 56%, 100% { opacity: 1; }
        20%, 24%, 55% { opacity: 0.5; }
    }

    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    @keyframes glow {
        0% { text-shadow: 0 0 5px var(--netflix-red); }
        50% { text-shadow: 0 0 20px var(--netflix-red), 0 0 30px var(--netflix-red); }
        100% { text-shadow: 0 0 5px var(--netflix-red); }
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    @keyframes bomb-glow {
        0% { text-shadow: 0 0 5px #fff, 0 0 10px #fff, 0 0 15px var(--netflix-red), 0 0 20px var(--netflix-red); }
        50% { text-shadow: 0 0 10px #fff, 0 0 20px #fff, 0 0 30px var(--netflix-red), 0 0 40px var(--netflix-red); }
        100% { text-shadow: 0 0 5px #fff, 0 0 10px #fff, 0 0 15px var(--netflix-red), 0 0 20px var(--netflix-red); }
    }

    .stApp {
        background: linear-gradient(135deg, var(--netflix-darker), var(--netflix-dark));
        color: var(--text);
        font-family: 'Exo 2', 'Helvetica Neue', 'Segoe UI', sans-serif;
        min-height: 100vh;
        overflow-x: hidden;
        position: relative;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 10% 20%, rgba(229, 9, 20, 0.05) 0%, transparent 20%),
            radial-gradient(circle at 90% 80%, rgba(229, 9, 20, 0.05) 0%, transparent 20%),
            radial-gradient(circle at 50% 50%, rgba(229, 9, 20, 0.03) 0%, transparent 30%);
        pointer-events: none;
        z-index: -1;
    }

    .stApp::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            linear-gradient(45deg, 
                transparent 30%, 
                rgba(229, 9, 20, 0.03) 50%, 
                transparent 70%
            );
        z-index: -1;
        opacity: 0.3;
        animation: rotate 20s linear infinite;
    }

    .auth-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.2rem;
        background: var(--card-bg);
        border-radius: 8px;
        box-shadow: 
            0 0 30px rgba(229, 9, 20, 0.2),
            0 0 60px rgba(229, 9, 20, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.08);
        position: relative;
        overflow: hidden;
        animation: float 6s ease-in-out infinite;
    }

    .auth-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        transform: scaleX(0);
        transform-origin: left;
        animation: 
            shine 3s ease-in-out infinite,
            pulse 2s infinite;
    }

    .auth-container::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            linear-gradient(
                45deg, 
                transparent 30%, 
                rgba(229, 9, 20, 0.03) 50%, 
                transparent 70%
            );
        z-index: -1;
        opacity: 0.5;
        animation: rotate 20s linear infinite;
    }

    .logo-container {
        text-align: center;
        margin-bottom: 1.8rem;
        position: relative;
        padding: 0.5rem 0;
    }

    .logo {
        font-size: 3.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
        text-shadow: 
            0 0 10px rgba(229, 9, 20, 0.3),
            0 0 20px rgba(229, 9, 20, 0.2);
        position: relative;
        display: inline-block;
        font-family: 'Orbitron', sans-serif;
        animation: glow 2s infinite;
    }

    /* FIXED BOMB EMOJI - MORE VISIBLE WITH GLOW EFFECT */
    .logo-bomb {
        position: absolute;
        top: -10px;
        right: -30px;
        font-size: 2.3rem;
        animation: bomb-glow 1.5s infinite, bounce 1.5s infinite;
        text-shadow: 0 0 5px #fff, 0 0 10px #fff, 0 0 15px var(--netflix-red), 0 0 20px var(--netflix-red);
    }

    .logo span {
        background: linear-gradient(90deg, #ff3366, var(--netflix-red));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-weight: 900;
    }

    .logo-subtitle {
        font-size: 1.1rem;
        color: var(--text-secondary);
        opacity: 0.9;
        text-align: center;
        line-height: 1.5;
        max-width: 80%;
        margin: 0 auto;
        font-weight: 500;
        animation: flicker 3s infinite;
    }

    .form-title {
        color: var(--text);
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1.2rem;
        text-align: center;
        position: relative;
    }

    .form-title::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 50px;
        height: 3px;
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        border-radius: 3px;
    }

    .stTextInput > div > div > input,
    .stTextInput > div > div > input:focus {
        background-color: #222222;
        color: var(--text);
        border: 1px solid #454545;
        border-radius: 4px;
        padding: 0.9rem 1.2rem;
        font-size: 1.1rem;
        height: auto;
        transition: all 0.3s ease;
        box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.2);
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--netflix-red);
        box-shadow: 
            0 0 0 2px rgba(229, 9, 20, 0.2),
            inset 0 0 5px rgba(229, 9, 20, 0.3);
    }

    .netflix-button {
        background: linear-gradient(90deg, var(--netflix-red), #b3070f);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.9rem 1.4rem;
        font-weight: 700;
        transition: all 0.3s ease;
        width: 100%;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
        margin-top: 1rem;
        cursor: pointer;
        position: relative;
        overflow: hidden;
        box-shadow: 0 5px 15px rgba(229, 9, 20, 0.3);
        font-family: 'Exo 2', sans-serif;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        animation: explosion 0.5s infinite alternate;
    }

    .netflix-button:hover {
        background: linear-gradient(90deg, #ff3366, #e50914);
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
        animation: none;
    }

    .netflix-button:active {
        transform: translateY(0);
        box-shadow: 0 2px 10px rgba(229, 9, 20, 0.3);
    }

    .netflix-button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(
            90deg, 
            transparent, 
            rgba(255, 255, 255, 0.2), 
            transparent
        );
        transition: all 0.6s;
    }

    .netflix-button:hover::before {
        left: 100%;
    }

    .divider {
        text-align: center;
        position: relative;
        margin: 1.8rem 0;
    }

    .divider::before,
    .divider::after {
        content: '';
        position: absolute;
        top: 50%;
        width: 45%;
        height: 1px;
        background: var(--border);
        transform: translateY(-50%);
    }

    .divider::before {
        left: 0;
    }

    .divider::after {
        right: 0;
    }

    .divider span {
        position: relative;
        background: var(--netflix-dark);
        padding: 0 15px;
        color: var(--text-secondary);
        font-size: 0.95rem;
        font-weight: 500;
        letter-spacing: 1px;
        background: rgba(20, 20, 40, 0.7);
        border-radius: 20px;
        backdrop-filter: blur(5px);
    }

    .status-message {
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
        text-align: center;
        opacity: 1;
        font-weight: 500;
        animation: fadeIn 0.4s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .status-success {
        background-color: rgba(11, 232, 129, 0.15);
        color: var(--success);
        border: 1px solid rgba(11, 232, 129, 0.3);
    }

    .status-error {
        background-color: rgba(255, 71, 87, 0.15);
        color: var(--highlight);
        border: 1px solid rgba(255, 71, 87, 0.3);
    }

    .status-info {
        background-color: rgba(229, 9, 20, 0.15);
        color: var(--netflix-red);
        border: 1px solid rgba(229, 9, 20, 0.3);
    }

    .logout-button {
        position: absolute;
        top: 20px;
        right: 20px;
        background: linear-gradient(90deg, rgba(229, 9, 20, 0.2), rgba(179, 7, 15, 0.2));
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 30px;
        padding: 0.5rem 1.2rem;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.3s ease;
        z-index: 100;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(229, 9, 20, 0.2);
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        animation: pulse 2s infinite;
    }

    .logout-button:hover {
        background: linear-gradient(90deg, rgba(229, 9, 20, 0.3), rgba(179, 7, 15, 0.3));
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(229, 9, 20, 0.3);
    }

    .logout-button::after {
        content: '🚪';
        font-size: 1.2rem;
    }

    .password-strength {
        margin-top: 0.4rem;
        font-size: 0.85rem;
        color: var(--text-secondary);
        display: flex;
        gap: 8px;
        align-items: center;
    }

    .password-strength-label {
        min-width: 100px;
        font-weight: 500;
    }

    .password-strength-bar {
        flex: 1;
        height: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        overflow: hidden;
    }

    .password-strength-fill {
        height: 100%;
        border-radius: 4px;
        width: 0%;
        transition: width 0.4s ease, background-color 0.4s ease;
    }

    .form-section {
        margin-bottom: 2.2rem;
        padding-bottom: 1.8rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        position: relative;
    }

    .form-section:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }

    .form-section::before {
        content: '';
        position: absolute;
        bottom: -1px;
        left: 0;
        width: 100%;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--netflix-red), transparent);
        transform: scaleX(0);
        transform-origin: left;
        transition: transform 0.4s ease;
    }

    .form-section:hover::before {
        transform: scaleX(1);
    }

    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1.2rem;
        color: var(--netflix-red);
        font-weight: 600;
        font-size: 1.3rem;
    }

    .section-title::before {
        content: '•';
        color: var(--netflix-red);
        font-size: 1.8rem;
        line-height: 0.6;
        animation: pulse 2s infinite;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.2rem;
        margin-top: 1.8rem;
    }

    .feature-card {
        background: rgba(30, 30, 30, 0.7);
        border-radius: 6px;
        padding: 1.2rem;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.08);
        position: relative;
        overflow: hidden;
        animation: float 6s ease-in-out infinite;
        box-shadow: 0 0 10px rgba(229, 9, 20, 0.1);
    }

    .feature-card:hover {
        transform: translateY(-5px);
        border-color: var(--netflix-red);
        box-shadow: 0 10px 25px rgba(229, 9, 20, 0.3);
        animation: none;
    }

    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--netflix-red);
    }

    .feature-icon {
        font-size: 1.8rem;
        margin-bottom: 0.5rem;
        color: var(--netflix-red);
        animation: bounce 2s infinite;
    }

    .feature-card h4 {
        color: white;
        margin-bottom: 0.4rem;
        font-size: 1.1rem;
        font-weight: 600;
    }

    .feature-card p {
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.5;
        opacity: 0.9;
    }

    .footer {
        text-align: center;
        margin-top: 2rem;
        color: var(--text-secondary);
        font-size: 0.85rem;
        padding: 1rem 0 0.6rem;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .footer a {
        color: var(--netflix-red);
        text-decoration: none;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    .footer a:hover {
        color: #ff3366;
        text-decoration: underline;
    }

    .loader {
        display: inline-block;
        width: 18px;
        height: 18px;
        border: 3px solid rgba(255, 255, 255, 0.3);
        border-radius: 50%;
        border-top-color: var(--netflix-red);
        animation: spin 1s ease-in-out infinite;
        margin-right: 8px;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .redirect-message {
        text-align: center;
        padding: 1.2rem;
        background: rgba(229, 9, 20, 0.08);
        border-radius: 6px;
        margin: 1.2rem 0;
        border: 1px solid rgba(229, 9, 20, 0.15);
        animation: pulse 2s infinite;
    }

    .redirect-message h3 {
        color: var(--netflix-red);
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-size: 1.1rem;
        font-weight: 600;
    }

    .redirect-message p {
        color: var(--text-secondary);
        font-size: 0.95rem;
    }

    .glow-text {
        text-shadow: 0 0 10px rgba(229, 9, 20, 0.3);
    }

    .nav-buttons {
        display: flex;
        justify-content: center;
        gap: 0.8rem;
        margin: 1.2rem auto;
        max-width: 600px;
        padding: 0 1rem;
    }

    .nav-button {
        flex: 1;
        background: rgba(255, 255, 255, 0.08);
        color: var(--text-secondary);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 0.5rem 0;
        cursor: default;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        text-align: center;
        position: relative;
    }

    .nav-button.active {
        background: var(--netflix-red);
        color: white;
        border-color: var(--netflix-red);
        font-weight: 600;
        box-shadow: 0 0 0 2px rgba(229, 9, 20, 0.2);
    }

    .nav-button.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 2px;
        background: var(--text);
        transition: transform 0.3s ease;
    }

    .nav-button.active:hover::after {
        transform: scaleX(1);
    }

    @media (max-width: 768px) {
        .auth-container {
            margin: 1rem auto;
            padding: 1.5rem;
        }

        .logo {
            font-size: 2.8rem;
        }

        .form-title {
            font-size: 1.5rem;
        }

        .feature-grid {
            grid-template-columns: 1fr;
        }

        .logout-button {
            padding: 0.4rem 1rem;
            font-size: 0.85rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Register user (with validation)
def register_user(username: str, password: str):
    # Password strength validation
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."

    if not re.search(r'[\W_]', password):
        return False, "Password must contain at least one special character."

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists."

        password_hash, salt = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, is_premium, created_at) VALUES (?, ?, ?, 0, datetime('now'))",
            (username, password_hash, salt)
        )
        conn.commit()
        return True, "Account created successfully!"
    except Exception as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

# Login function with security features
def login_user(username: str, password: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if account is locked
        cursor.execute("SELECT lockout_end FROM users WHERE username = ?", (username,))
        lockout_end = cursor.fetchone()
        if lockout_end and lockout_end[0] and datetime.now() < datetime.fromisoformat(lockout_end[0]):
            conn.close()
            return False, "Account is locked. Please wait before trying again."

        # Check user existence
        cursor.execute("SELECT password_hash, salt, login_attempts, lockout_end FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, "Invalid username or password."

        # Reset login attempts if successful
        if row[0] == hash_password(password, row[1])[0]:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET login_attempts = 0, last_login = datetime('now') WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            return True, "Authentication successful!"

        # Handle failed login
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT login_attempts FROM users WHERE username = ?", (username,))
        current_attempts = cursor.fetchone()[0] or 0

        # Update login attempts
        cursor.execute("UPDATE users SET login_attempts = ? WHERE username = ?", (current_attempts + 1, username))

        # Lock account if exceeded max attempts
        if current_attempts + 1 >= MAX_LOGIN_ATTEMPTS:
            lockout_time = datetime.now() + timedelta(seconds=LOCKOUT_DURATION)
            cursor.execute("UPDATE users SET lockout_end = ? WHERE username = ?", (lockout_time.isoformat(), username))

        conn.commit()
        conn.close()

        # Calculate remaining attempts
        remaining_attempts = MAX_LOGIN_ATTEMPTS - (current_attempts + 1)
        return False, f"Invalid credentials. {remaining_attempts} attempt(s) remaining."
    except Exception as e:
        return False, f"Database error: {str(e)}"

# Main Authentication App
def main():
    # Initialize DB with error handling
    db_initialized = init_db()
    if not db_initialized:
        st.error("Failed to initialize database. Please check permissions.")
        st.stop()

    inject_custom_css()

    # Check if we should redirect (already logged in)
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        # Show logout button with proper functionality
        st.markdown("""
        <button class="logout-button" id="logout-btn">
            Logout
        </button>
        <script>
        document.getElementById('logout-btn').addEventListener('click', function() {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/clear_session', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4) {
                    window.location.href = window.location.pathname;
                }
            };
            xhr.send(JSON.stringify({clear: true}));
        });
        </script>
        """, unsafe_allow_html=True)

        # Use st.switch_page instead of JavaScript redirects
        if 'is_admin' in st.session_state and st.session_state.is_admin:
            st.switch_page("pages/admin.py")
        elif 'is_premium' in st.session_state and st.session_state.is_premium:
            st.switch_page("pages/testing.py")
        else:
            st.switch_page("pages/RAG_Assistant.py")
        return

    # Navigation buttons - FIXED TO HIGHLIGHT CURRENT PAGE & WORKING LINKS
    st.markdown("""
    <div class="nav-buttons">
        <span class="nav-button active">Login</span>
        <a class="nav-button" href="/RAG_Assistant" target="_self" style="cursor:pointer; text-decoration:none; display:inline-block;">Free</a>
        <a class="nav-button" href="/testing" target="_self" style="cursor:pointer; text-decoration:none; display:inline-block;">Pro</a>
        <a class="nav-button" href="/mock_interview" target="_self" style="cursor:pointer; text-decoration:none; display:inline-block; border-color:#3B82F6; color:#60A5FA;">🎯 Mock Interview</a>
        <a class="nav-button" href="/AksharaMitra" target="_self" style="cursor:pointer; text-decoration:none; display:inline-block; border-color:#14B8A6; color:#5EEAD4;">📖 AksharaMitra</a>
    </div>
    """, unsafe_allow_html=True)

    ln_c1, ln_c2, ln_c3, ln_c4 = st.columns(4)
    with ln_c1:
        if st.button("📚 RAG Assistant", key="login_to_rag_btn", use_container_width=True):
            st.switch_page("pages/RAG_Assistant.py")
    with ln_c2:
        if st.button("⚡ Pro Assistant", key="login_to_pro_btn", use_container_width=True):
            st.switch_page("pages/testing.py")
    with ln_c3:
        if st.button("🎯 Mock Interview", key="login_to_mock_btn", type="primary", use_container_width=True):
            st.switch_page("pages/mock_interview.py")
    with ln_c4:
        if st.button("📖 AksharaMitra", key="login_to_akshara_btn", use_container_width=True):
            st.switch_page("pages/AksharaMitra.py")

    # Auth container
    with st.container():
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)

        # Logo with Netflix styling and CRAZY animation
        st.markdown("""
        <div class="logo-container">
            <h1 class="logo">
                RAG<span>Assistant</span>
                <div class="logo-bomb">💥</div>
            </h1>
            <div class="logo-subtitle">
                Unlock the power of your documents with AI-powered search and analysis
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Login Form - Always visible at the top
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<h2 class="form-title glow-text">Sign In</h2>', unsafe_allow_html=True)

        # Login form
        login_username = st.text_input("Username", key="login_user", placeholder="Your username")
        login_password = st.text_input("Password", type="password", key="login_pass", placeholder="Your password")

        # Sign In button
        if st.button("Sign In", key="login_btn", use_container_width=True):
            if not login_username or not login_password:
                st.markdown('<div class="status-error">Please enter both username and password.</div>', unsafe_allow_html=True)
            else:
                success, message = login_user(login_username, login_password)

                if success:
                    # Update session state
                    st.session_state.logged_in = True
                    st.session_state.username = login_username

                    # Get user role (including admin status)
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("SELECT is_premium, is_admin FROM users WHERE username = ?", (login_username,))
                        row = cursor.fetchone()
                        conn.close()

                        if row:
                            st.session_state.is_premium = bool(row[0])
                            st.session_state.is_admin = bool(row[1])  # Store admin status
                        else:
                            st.session_state.is_premium = False
                            st.session_state.is_admin = False
                    except Exception as e:
                        st.session_state.is_premium = False
                        st.session_state.is_admin = False

                    # Show success message
                    st.markdown('''
                    <div class="redirect-message">
                        <h3><span class="loader"></span> Authentication successful!</h3>
                        <p>Redirecting to your dashboard...</p>
                    </div>
                    ''', unsafe_allow_html=True)

                    # Use st.switch_page instead of JavaScript redirects
                    time.sleep(1.5)
                    if st.session_state.is_admin:
                        st.switch_page("pages/admin.py")
                    elif st.session_state.is_premium:
                        st.switch_page("pages/testing.py")
                    else:
                        st.switch_page("pages/RAG_Assistant.py")
                else:
                    st.markdown(f'<div class="status-error">{message}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Divider
        st.markdown('<div class="divider"><span>OR</span></div>', unsafe_allow_html=True)

        # Signup Form - Always visible directly below login form
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown('<h2 class="form-title">Create Account</h2>', unsafe_allow_html=True)

        # Registration form
        reg_username = st.text_input("Username", key="reg_user", placeholder="Choose a username")
        reg_password = st.text_input("Password", type="password", key="reg_pass", placeholder="At least 8 characters")
        confirm_password = st.text_input("Confirm Password", type="password", key="conf_pass", placeholder="Re-enter your password")

        # Password strength meter with Netflix styling
        if reg_password:
            strength = 0
            if len(reg_password) >= 8:
                strength += 1
            if re.search(r'[A-Z]', reg_password):
                strength += 1
            if re.search(r'[a-z]', reg_password):
                strength += 1
            if re.search(r'[0-9]', reg_password):
                strength += 1
            if re.search(r'[\W_]', reg_password):
                strength += 1

            # Calculate strength percentage
            strength_percent = (strength / 5) * 100

            # Set color based on strength
            if strength_percent < 40:
                strength_color = "#ff4757"
            elif strength_percent < 70:
                strength_color = "#ffa502"
            else:
                strength_color = "#00e676"

            st.markdown(f'''
            <div class="password-strength">
                <div class="password-strength-label">Strength:</div>
                <div class="password-strength-bar">
                    <div class="password-strength-fill" style="width: {strength_percent}%; background: {strength_color};"></div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

        # Create Account button
        if st.button("Create Account", key="register_btn", use_container_width=True):
            if not reg_username or not reg_password:
                st.markdown('<div class="status-error">All fields are required.</div>', unsafe_allow_html=True)
            elif reg_password != confirm_password:
                st.markdown('<div class="status-error">Passwords do not match!</div>', unsafe_allow_html=True)
            else:
                success, msg = register_user(reg_username, reg_password)
                if success:
                    st.markdown(f'<div class="status-success">{msg}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="status-info">Redirecting to login...</div>', unsafe_allow_html=True)
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.markdown(f'<div class="status-error">{msg}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Feature highlights with Netflix styling
        st.markdown("""
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h4>AI-Powered Search</h4>
                <p>Find information across your documents using advanced semantic search technology</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">💡</div>
                <h4>Source Verification</h4>
                <p>Every answer is backed by citations from your documents with precise references</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h4>Document Analytics</h4>
                <p>Gain insights into document patterns, key topics, and information gaps</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Footer
        st.markdown('<div class="footer">© 2023 RAG Assistant | <a href="#">Privacy</a> • <a href="#">Terms</a> • <a href="#">Contact</a></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
