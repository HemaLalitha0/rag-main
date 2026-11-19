
import streamlit as st
import sqlite3
import os
import time
from pathlib import Path

# FIX: Reliable database path that works everywhere
try:
    # Get the directory of the main app (2 levels up from pages/admin.py)
    MAIN_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(MAIN_APP_DIR, 'users.db')
except:
    # Fallback to current directory
    DB_PATH = 'users.db'

def inject_admin_css():
    """Inject ULTRA-CRAZY Netflix-themed CSS for admin panel"""
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

    .nav-buttons {
        display: flex;
        justify-content: center;
        gap: 0.8rem;
        margin: 1.2rem auto;
        max-width: 800px;
        padding: 0 1rem;
    }

    .nav-button {
        flex: 1;
        background: rgba(255, 255, 255, 0.08);
        color: var(--text-secondary);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.9rem;
        text-align: center;
        position: relative;
        font-family: 'Exo 2', sans-serif;
        font-weight: 500;
        letter-spacing: 0.5px;
        animation: float 6s ease-in-out infinite;
    }

    .nav-button:hover {
        background: rgba(255, 255, 255, 0.15);
        transform: translateY(-3px);
    }

    .nav-button.active {
        background: var(--netflix-red);
        color: white;
        border-color: var(--netflix-red);
        font-weight: 600;
        box-shadow: 0 0 0 2px rgba(229, 9, 20, 0.2);
        animation: none;
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

    .admin-container {
        max-width: 1000px;
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

    .admin-container::before {
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

    .admin-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        text-align: center;
        margin-bottom: 1.5rem;
        letter-spacing: -1px;
        text-shadow: 0 0 10px rgba(229, 9, 20, 0.3);
        font-family: 'Orbitron', sans-serif;
        animation: glow 2s infinite;
    }

    .admin-subtitle {
        font-size: 1.2rem;
        color: var(--text-secondary);
        opacity: 0.9;
        text-align: center;
        margin-bottom: 2rem;
        animation: flicker 3s infinite;
    }

    .user-card {
        background: rgba(30, 30, 30, 0.7);
        border-radius: 6px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: all 0.3s ease;
        position: relative;
        animation: float 6s ease-in-out infinite;
        box-shadow: 0 0 10px rgba(229, 9, 20, 0.1);
    }

    .user-card:hover {
        transform: translateY(-5px);
        border-color: var(--netflix-red);
        box-shadow: 0 10px 25px rgba(229, 9, 20, 0.3);
        animation: none;
    }

    .user-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: var(--netflix-red);
    }

    .user-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .user-name {
        font-size: 1.4rem;
        font-weight: 600;
        color: var(--text);
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .user-admin-badge {
        background: var(--netflix-red);
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        animation: pulse 2s infinite;
    }

    .user-id {
        color: var(--text-secondary);
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    .user-controls {
        display: flex;
        gap: 1.5rem;
        margin-top: 1rem;
    }

    .control-label {
        font-weight: 500;
        color: var(--text-secondary);
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }

    .toggle-switch {
        position: relative;
        display: inline-block;
        width: 50px;
        height: 24px;
    }

    .toggle-switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 24px;
    }

    .slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 4px;
        bottom: 4px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
    }

    input:checked + .slider {
        background-color: var(--netflix-red);
    }

    input:checked + .slider:before {
        transform: translateX(26px);
    }

    .stat-card {
        background: rgba(229, 9, 20, 0.1);
        border-radius: 6px;
        padding: 1.2rem;
        text-align: center;
        border-left: 4px solid var(--netflix-red);
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(229, 9, 20, 0.2);
    }

    .stat-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin: 0.5rem 0;
        animation: glow 2s infinite;
    }

    .stat-label {
        color: var(--text-secondary);
        font-size: 0.95rem;
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

    .status-changed {
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

    .admin-sidebar {
        background: rgba(20, 20, 20, 0.7);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .admin-sidebar h3 {
        color: var(--netflix-red);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .admin-sidebar p {
        color: var(--text-secondary);
        margin: 0.5rem 0;
    }

    .refresh-button {
        background: linear-gradient(90deg, var(--netflix-red), #b3070f);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 700;
        transition: all 0.3s ease;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        width: 100%;
        animation: explosion 0.5s infinite alternate;
    }

    .refresh-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(229, 9, 20, 0.3);
        animation: none;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 var(--netflix-red); }
        70% { box-shadow: 0 0 0 15px rgba(229, 9, 20, 0); }
        100% { box-shadow: 0 0 0 0 rgba(229, 9, 20, 0); }
    }

    .pulse {
        animation: pulse 2s infinite;
    }

    .admin-icon {
        color: var(--netflix-red);
        font-size: 1.5rem;
        margin-right: 0.5rem;
    }

    .user-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.2rem;
        margin-bottom: 1.5rem;
    }

    .vibe-code {
        text-align: center;
        margin-top: 1.5rem;
        font-size: 1.2rem;
        color: var(--text-secondary);
        opacity: 0.8;
    }

    .vibe-code span {
        background: linear-gradient(90deg, var(--netflix-red), #ff3366);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-weight: 600;
        animation: glow 2s infinite;
    }

    .vibe-code::after {
        content: '💥';
        animation: bounce 1.5s infinite;
        margin-left: 8px;
        font-size: 1.4rem;
    }

    .change-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        animation: fadeIn 0.3s, fadeOut 0.3s 2.7s;
    }

    @keyframes fadeOut {
        to { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)

def check_admin():
    """Verify if current user is admin"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        st.warning("Please log in first.")
        if st.button("Go to Login", key="admin_login_btn"):
            st.switch_page("pages/login.py")
        st.stop()
        return False

    # Get admin status from database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (st.session_state.username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            st.session_state.is_admin = True
            return True
        else:
            st.session_state.is_admin = False
    except Exception as e:
        st.error(f"Database error checking admin status: {str(e)}")

    st.error("This page is for administrators only.")
    st.info("Contact your system administrator for access.")
    if st.button("Back to Home", key="admin_home_btn"):
        st.switch_page("pages/RAG_Assistant.py")
    st.stop()
    return False

def get_all_users():
    """Fetch all users from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, is_premium, is_admin FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        st.error(f"Database path: {DB_PATH}")
        return []

def toggle_premium(user_id, is_premium):
    """Toggle premium status for a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_premium = ? WHERE id = ?",
            (1 if is_premium else 0, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to update premium status: {str(e)}")
        return False

def toggle_admin(user_id, is_admin):
    """Toggle admin status for a user"""
    try:
        # Prevent demoting the only admin
        if not is_admin:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            admin_count = cursor.fetchone()[0]
            conn.close()

            if admin_count <= 1:
                st.warning("Cannot remove admin rights - at least one admin must exist.")
                return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET is_admin = ? WHERE id = ?",
            (1 if is_admin else 0, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to update admin status: {str(e)}")
        return False

def main():
    # Inject Netflix theme CSS
    inject_admin_css()

    # Check if user is admin
    if not check_admin():
        return

    # Navigation buttons with Admin highlighted
    st.markdown("""
    <div class="nav-buttons">
        <div class="nav-button">Login</div>
        <div class="nav-button">Free</div>
        <div class="nav-button">Pro</div>
        <div class="nav-button active">Admin</div>
    </div>
    """, unsafe_allow_html=True)

    # Proper logout button implementation - THIS IS THE CORRECT WAY
    if st.button(" Logout", key="logout_btn", use_container_width=True):
        # Clear ALL authentication-related session state
        st.session_state.logged_in = False
        if 'username' in st.session_state:
            del st.session_state.username
        if 'is_premium' in st.session_state:
            del st.session_state.is_premium
        if 'is_admin' in st.session_state:
            del st.session_state.is_admin
        if 'user_id' in st.session_state:
            del st.session_state.user_id

        # Force immediate rerun to update UI
        st.rerun()

    # Main admin container
    with st.container():
        st.markdown('<div class="admin-container">', unsafe_allow_html=True)

        # Admin title and subtitle
        st.markdown('<h1 class="admin-title">Admin Panel <span style="font-size:2.5rem; animation: bounce 14.5s infinite;">💥</span></h1>', unsafe_allow_html=True)
        st.markdown('<p class="admin-subtitle">Manage users and their premium status</p>', unsafe_allow_html=True)

        # Admin sidebar with stats
        st.markdown('<div class="admin-sidebar">', unsafe_allow_html=True)

        # Get all users for stats
        users = get_all_users()
        total_users = len(users)
        premium_users = sum(1 for _, _, is_premium, _ in users if is_premium)
        admin_users = sum(1 for _, _, _, is_admin in users if is_admin)

        st.markdown('<h3><span class="admin-icon">System</span>Statistics</h3>', unsafe_allow_html=True)
        st.markdown('<div class="user-stats">', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-label">Total Users</div>
            <div class="stat-value">{total_users}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-label">Premium Users</div>
            <div class="stat-value">{premium_users}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown(f'''
        <div class="stat-card">
            <div class="stat-label">Admin Users</div>
            <div class="stat-value">{admin_users}</div>
        </div>
        ''', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close user-stats
        st.markdown('</div>', unsafe_allow_html=True)  # Close admin-sidebar

        # Refresh button with proper functionality
        if st.button("Refresh User List", key="refresh_btn", use_container_width=True):
            st.rerun()

        # Get all users
        users = get_all_users()

        if not users:
            st.markdown('<div class="status-info">No users found in the database.</div>', unsafe_allow_html=True)
            st.stop()

        # Display user list
        st.markdown(f'<h2 class="form-title" style="text-align:center;margin-bottom:1.5rem;">User Management</h2>', unsafe_allow_html=True)

        # Create a table for users
        for i, user in enumerate(users):
            user_id, username, is_premium, is_admin = user

            # FIXED: Properly display admin badge without showing HTML code
            admin_badge = ' (Admin)' if is_admin else ''
            with st.expander(f"👤 {username}{admin_badge}", expanded=False):
                st.markdown('<div class="user-card">', unsafe_allow_html=True)

                # User header
                st.markdown('<div class="user-header">', unsafe_allow_html=True)
                st.markdown(f'<div class="user-name">👤 {username}</div>', unsafe_allow_html=True)
                if is_admin:
                    st.markdown('<div class="user-admin-badge">Admin</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # User ID
                st.markdown(f'<div class="user-id">ID: {user_id}</div>', unsafe_allow_html=True)

                # User controls
                st.markdown('<div class="user-controls">', unsafe_allow_html=True)

                # Premium toggle - FIXED: Use Streamlit's native checkbox
                st.markdown('<div class="control-label">Premium Status</div>', unsafe_allow_html=True)
                current_premium = bool(is_premium)

                # Use Streamlit's native checkbox for premium
                new_premium = st.checkbox(
                    "Premium",
                    value=current_premium,
                    key=f"premium_{user_id}",
                    label_visibility="collapsed"
                )

                # Check if the value changed
                if new_premium != current_premium:
                    if toggle_premium(user_id, new_premium):
                        # Show success message
                        st.success(f"User '{username}' is now {'a Premium' if new_premium else 'not a Premium'} member!")
                        # Force refresh after update
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(f"Failed to update premium status for {username}")

                # Admin toggle (only show if not current user)
                if user_id != st.session_state.get('user_id', 0) or st.session_state.username != "admin":
                    st.markdown('<div class="control-label">Admin Status</div>', unsafe_allow_html=True)
                    current_admin = bool(is_admin)

                    # Use Streamlit's native checkbox for admin
                    new_admin = st.checkbox(
                        "Admin",
                        value=current_admin,
                        key=f"admin_{user_id}",
                        label_visibility="collapsed"
                    )

                    # Check if the value changed
                    if new_admin != current_admin:
                        if toggle_admin(user_id, new_admin):
                            # Show success message
                            st.success(f"User '{username}' is now {'an Admin' if new_admin else 'not an Admin'}!")
                            # Force refresh after update
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error(f"Failed to update admin status for {username}")
                else:
                    st.markdown('<div class="control-label">Admin Status</div>', unsafe_allow_html=True)
                    st.markdown('<div>You (cannot modify) 🔒</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)  # Close user-controls
                st.markdown('</div>', unsafe_allow_html=True)  # Close user-card

        # Add the "I Coded" text with emoji
        st.markdown('<div class="vibe-code">RAG Assistant\'s <span>Admin</span> panel</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # Close admin-container

if __name__ == "__main__":
    main()
