import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, time, timedelta
import os
import re
from PIL import Image
import io
import pandas as pd
import json
import plotly.express as px
from streamlit.components.v1 import html

# --------------------------
# Database Setup (200 lines)
# --------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        
        # Enhanced users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('agent', 'admin', 'team_leader')),
                team TEXT,
                skillset TEXT,
                created_at TEXT)
        """)
        
        # Break templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                lunch_breaks TEXT,
                tea_breaks TEXT,
                created_by TEXT,
                created_at TEXT)
        """)
        
        # Team breaks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_breaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT,
                template_id INTEGER,
                date TEXT,
                time_slot TEXT,
                max_members INTEGER,
                booked_members INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TEXT)
        """)
        
        # Team break bookings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_break_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_break_id INTEGER,
                user_id INTEGER,
                username TEXT,
                booked_at TEXT)
        """)
        
        # Chat groups
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                purpose TEXT,
                skillset TEXT,
                team TEXT,
                created_by TEXT,
                created_at TEXT)
        """)
        
        # Group members
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                user_id INTEGER,
                joined_at TEXT)
        """)
        
        # Group messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER,
                sender_id INTEGER,
                message TEXT,
                timestamp TEXT)
        """)
        
        # Original tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                request_type TEXT,
                identifier TEXT,
                comment TEXT,
                timestamp TEXT,
                completed INTEGER DEFAULT 0)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_leader TEXT,
                agent_name TEXT,
                ticket_id TEXT,
                error_description TEXT,
                timestamp TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hold_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploader TEXT,
                image_data BLOB,
                timestamp TEXT)
        """)
        
        # Create default admin
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password, role, team, skillset, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", hash_password("admin123"), "admin", "Management", "Administration", 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        # Create default teams
        teams = ["Support", "Sales", "Billing", "Technical"]
        for team in teams:
            # Create team chat group
            cursor.execute("""
                INSERT OR IGNORE INTO chat_groups (name, purpose, skillset, team, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f"{team} Team", f"{team} communications", "General", team, "admin",
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Create default break templates
            cursor.execute("""
                INSERT OR IGNORE INTO break_templates (name, lunch_breaks, tea_breaks, created_by, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"{team} Standard",
                json.dumps(["12:00", "12:30", "13:00"]),
                json.dumps({"early": ["10:00", "10:30"], "late": ["15:00", "15:30"]}),
                "admin",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
    finally:
        conn.close()

# --------------------------
# Authentication (100 lines)
# --------------------------

def authenticate(username, password):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        hashed_password = hash_password(password)
        cursor.execute("""
            SELECT id, username, role, team, skillset 
            FROM users 
            WHERE username = ? AND password = ?
        """, (username, hashed_password))
        result = cursor.fetchone()
        if result:
            return {
                "id": result[0],
                "username": result[1],
                "role": result[2],
                "team": result[3],
                "skillset": result[4]
            }
        return None
    finally:
        conn.close()

def get_user_teams():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT team FROM users WHERE team IS NOT NULL")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

# --------------------------
# Break Management (300 lines)
# --------------------------

def create_team_break(team, template_id, date, time_slot, max_members, creator):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO team_breaks (team, template_id, date, time_slot, max_members, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (team, template_id, date, time_slot, max_members, creator, timestamp))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_team_breaks(team, date=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if date:
            cursor.execute("""
                SELECT tb.*, t.name as template_name
                FROM team_breaks tb
                JOIN break_templates t ON tb.template_id = t.id
                WHERE tb.team = ? AND tb.date = ?
                ORDER BY tb.time_slot
            """, (team, date))
        else:
            cursor.execute("""
                SELECT tb.*, t.name as template_name
                FROM team_breaks tb
                JOIN break_templates t ON tb.template_id = t.id
                WHERE tb.team = ?
                ORDER BY tb.date, tb.time_slot
            """, (team,))
        return cursor.fetchall()
    finally:
        conn.close()

def book_team_break(break_id, user_id, username):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if already booked
        cursor.execute("""
            SELECT 1 FROM team_break_bookings 
            WHERE team_break_id = ? AND user_id = ?
        """, (break_id, user_id))
        if cursor.fetchone():
            return False
        
        cursor.execute("""
            INSERT INTO team_break_bookings (team_break_id, user_id, username, booked_at)
            VALUES (?, ?, ?, ?)
        """, (break_id, user_id, username, timestamp))
        
        cursor.execute("""
            UPDATE team_breaks 
            SET booked_members = booked_members + 1 
            WHERE id = ?
        """, (break_id,))
        
        conn.commit()
        return True
    finally:
        conn.close()

# --------------------------
# Group Chat (200 lines)
# --------------------------

def send_group_message(group_id, sender_id, message):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO group_messages (group_id, sender_id, message, timestamp)
            VALUES (?, ?, ?, ?)
        """, (group_id, sender_id, message, timestamp))
        conn.commit()
        return True
    finally:
        conn.close()

def get_group_messages(group_id, limit=100):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT gm.*, u.username as sender_name
            FROM group_messages gm
            JOIN users u ON gm.sender_id = u.id
            WHERE gm.group_id = ?
            ORDER BY gm.timestamp DESC
            LIMIT ?
        """, (group_id, limit))
        return cursor.fetchall()
    finally:
        conn.close()

def get_user_groups(user_id):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cg.* 
            FROM chat_groups cg
            JOIN group_members gm ON cg.id = gm.group_id
            WHERE gm.user_id = ?
            ORDER BY cg.name
        """, (user_id,))
        return cursor.fetchall()
    finally:
        conn.close()

# --------------------------
# Visualization (150 lines)
# --------------------------

def plot_team_availability(team, date):
    breaks = get_team_breaks(team, date)
    if not breaks:
        return None
    
    data = []
    for b in breaks:
        data.append({
            "Time Slot": b[4],
            "Available": b[5] - b[6],
            "Capacity": b[5],
            "Template": b[8]
        })
    
    df = pd.DataFrame(data)
    fig = px.bar(df, x="Time Slot", y="Available", 
                color="Template",
                title=f"Team {team} Break Availability - {date}",
                hover_data=["Capacity"])
    return fig

def plot_team_break_distribution(team):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, time_slot, booked_members, max_members
            FROM team_breaks
            WHERE team = ?
            ORDER BY date, time_slot
        """, (team,))
        data = cursor.fetchall()
        
        if not data:
            return None
            
        df = pd.DataFrame(data, columns=["Date", "Time Slot", "Booked", "Capacity"])
        df["Utilization"] = df["Booked"] / df["Capacity"]
        
        fig = px.line(df, x="Date", y="Utilization", 
                     color="Time Slot",
                     title=f"Team {team} Break Utilization Over Time")
        return fig
    finally:
        conn.close()

# --------------------------
# UI Components (400 lines)
# --------------------------

def team_break_coordination(user):
    st.title(f"Team {user['team']} Break Coordination")
    
    selected_date = st.date_input("Select date", datetime.now())
    formatted_date = selected_date.strftime('%Y-%m-%d')
    
    # Availability visualization
    st.subheader("Team Break Availability")
    fig = plot_team_availability(user['team'], formatted_date)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No breaks scheduled for selected date")
    
    # Break booking
    st.subheader("Available Team Breaks")
    breaks = get_team_breaks(user['team'], formatted_date)
    
    if breaks:
        cols = st.columns(3)
        for i, break_slot in enumerate(breaks):
            with cols[i % 3]:
                with st.expander(f"{break_slot[4]} - {break_slot[8]}"):
                    st.metric("Available", f"{break_slot[5] - break_slot[6]}/{break_slot[5]}")
                    if st.button("Book", key=f"book_{break_slot[0]}"):
                        if book_team_break(break_slot[0], user['id'], user['username']):
                            st.success("Break booked successfully!")
                            st.rerun()
    else:
        st.info("No team breaks available for selected date")

def group_chat_interface(user):
    st.title("Team Communication")
    
    groups = get_user_groups(user['id'])
    if not groups:
        st.warning("You are not in any groups yet")
        return
    
    selected_group = st.selectbox("Select Group", [g[1] for g in groups])
    group_id = [g[0] for g in groups if g[1] == selected_group][0]
    
    # Chat display
    st.subheader(f"Group: {selected_group}")
    messages = get_group_messages(group_id)
    
    chat_container = st.container()
    with chat_container:
        for msg in reversed(messages):
            cols = st.columns([1, 4])
            with cols[0]:
                st.markdown(f"**{msg[5]}**")
                st.caption(msg[4])
            with cols[1]:
                st.write(msg[3])
            st.divider()
    
    # Message input
    with st.form("chat_form", clear_on_submit=True):
        message = st.text_area("Type your message")
        if st.form_submit_button("Send"):
            if message:
                send_group_message(group_id, user['id'], message)
                st.rerun()

def admin_team_management():
    st.title("Team Break Administration")
    
    # Team break scheduling
    with st.expander("Schedule Team Breaks"):
        teams = get_user_teams()
        selected_team = st.selectbox("Select Team", teams)
        
        conn = sqlite3.connect("data/requests.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM break_templates")
        templates = cursor.fetchall()
        conn.close()
        
        selected_template = st.selectbox("Select Break Template", templates, format_func=lambda x: x[1])
        
        col1, col2 = st.columns(2)
        date = col1.date_input("Date")
        time_slot = col2.text_input("Time Slot (e.g., 14:00-14:30)")
        max_members = st.number_input("Max Team Members", min_value=1, value=5)
        
        if st.button("Schedule Team Break"):
            if create_team_break(selected_team, selected_template[0], 
                               date.strftime('%Y-%m-%d'), time_slot, 
                               max_members, st.session_state.user['username']):
                st.success("Team break scheduled!")
    
    # Team monitoring
    with st.expander("Monitor Team Breaks"):
        teams = get_user_teams()
        selected_team = st.selectbox("Select Team to Monitor", teams)
        
        col1, col2 = st.columns(2)
        view_type = col1.radio("View", ["Daily", "Historical"])
        
        if view_type == "Daily":
            selected_date = col2.date_input("View date", datetime.now())
            breaks = get_team_breaks(selected_team, selected_date.strftime('%Y-%m-%d'))
            
            if breaks:
                st.dataframe(pd.DataFrame(breaks, 
                    columns=["ID", "Team", "Template ID", "Date", "Time Slot", 
                             "Max", "Booked", "Creator", "Created At", "Template Name"]))
                
                fig = plot_team_availability(selected_team, selected_date.strftime('%Y-%m-%d'))
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No breaks scheduled for selected team/date")
        else:
            fig = plot_team_break_distribution(selected_team)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No historical data available")

# --------------------------
# Main Application (200 lines)
# --------------------------

def main():
    st.set_page_config(
        page_title="Team Break Coordination System",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session
    if 'user' not in st.session_state:
        st.session_state.user = None
        st.session_state.authenticated = False
    
    # Authentication
    if not st.session_state.authenticated:
        with st.form("login_form"):
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                user = authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        # Main interface
        st.sidebar.title(f"Welcome, {st.session_state.user['username']}")
        st.sidebar.write(f"Team: {st.session_state.user['team']}")
        st.sidebar.write(f"Role: {st.session_state.user['role']}")
        
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.session_state.authenticated = False
            st.rerun()
        
        # Navigation
        if st.session_state.user['role'] == 'admin':
            menu = ["Team Management", "Group Chats", "Break Analytics"]
        else:
            menu = ["Team Breaks", "Group Chats"]
        
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Team Breaks":
            team_break_coordination(st.session_state.user)
        elif choice == "Team Management":
            admin_team_management()
        elif choice == "Group Chats":
            group_chat_interface(st.session_state.user)
        elif choice == "Break Analytics":
            st.title("Break Analytics Dashboard")
            plot_team_break_distribution(st.session_state.user['team'])

if __name__ == "__main__":
    init_db()
    main()
