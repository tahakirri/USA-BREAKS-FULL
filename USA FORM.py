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

# --------------------------
# Database Functions
# --------------------------

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        hashed_password = hash_password(password)
        cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", 
                      (username, hashed_password))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('agent', 'admin')))
        """)
        
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
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp TEXT,
                mentions TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hold_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploader TEXT,
                image_data BLOB,
                timestamp TEXT)
        """)
        
        # Handle system_settings table schema migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE system_settings (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    killswitch_enabled INTEGER DEFAULT 0,
                    chat_killswitch_enabled INTEGER DEFAULT 0)
            """)
            cursor.execute("INSERT INTO system_settings (id, killswitch_enabled, chat_killswitch_enabled) VALUES (1, 0, 0)")
        else:
            cursor.execute("PRAGMA table_info(system_settings)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'chat_killswitch_enabled' not in columns:
                cursor.execute("ALTER TABLE system_settings ADD COLUMN chat_killswitch_enabled INTEGER DEFAULT 0")
                cursor.execute("UPDATE system_settings SET chat_killswitch_enabled = 0 WHERE id = 1")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                user TEXT,
                comment TEXT,
                timestamp TEXT,
                FOREIGN KEY(request_id) REFERENCES requests(id))
        """)
        
        # Create default admin account
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password, role) 
            VALUES (?, ?, ?)
        """, ("taha kirri", hash_password("arise@99"), "admin"))
        admin_accounts = [
            ("taha kirri", "arise@99"),
            ("Issam Samghini", "admin@2025"),
            ("Loubna Fellah", "admin@99"),
            ("Youssef Kamal", "admin@006"),
            ("Fouad Fathi", "admin@55")
        ]
        
        for username, password in admin_accounts:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role) 
                VALUES (?, ?, ?)
            """, (username, hash_password(password), "admin"))
        # Create agent accounts (agent name as username, workspace ID as password)
        agents = [
            ("Karabila Younes", "30866"),
            ("Kaoutar Mzara", "30514"),
            ("Ben Tahar Chahid", "30864"),
            ("Cherbassi Khadija", "30868"),
            ("Lekhmouchi Kamal", "30869"),
            ("Said Kilani", "30626"),
            ("AGLIF Rachid", "30830"),
            ("Yacine Adouha", "30577"),
            ("Manal Elanbi", "30878"),
            ("Jawad Ouassaddine", "30559"),
            ("Kamal Elhaouar", "30844"),
            ("Hoummad Oubella", "30702"),
            ("Zouheir Essafi", "30703"),
            ("Anwar Atifi", "30781"),
            ("Said Elgaouzi", "30782"),
            ("HAMZA SAOUI", "30716"),
            ("Ibtissam Mazhari", "30970"),
            ("Imad Ghazali", "30971"),
            ("Jamila Lahrech", "30972"),
            ("Nassim Ouazzani Touhami", "30973"),
            ("Salaheddine Chaggour", "30974"),
            ("Omar Tajani", "30711"),
            ("Nizar Remz", "30728"),
            ("Abdelouahed Fettah", "30693"),
            ("Amal Bouramdane", "30675"),
            ("Fatima Ezzahrae Oubaalla", "30513"),
            ("Redouane Bertal", "30643"),
            ("Abdelouahab Chenani", "30789"),
            ("Imad El Youbi", "30797"),
            ("Youssef Hammouda", "30791"),
            ("Anas Ouassifi", "30894"),
            ("SALSABIL ELMOUSS", "30723"),
            ("Hicham Khalafa", "30712"),
            ("Ghita Adib", "30710"),
            ("Aymane Msikila", "30722"),
            ("Marouane Boukhadda", "30890"),
            ("Hamid Boulatouan", "30899"),
            ("Bouchaib Chafiqi", "30895"),
            ("Houssam Gouaalla", "30891"),
            ("Abdellah Rguig", "30963"),
            ("Abdellatif Chatir", "30964"),
            ("Abderrahman Oueto", "30965"),
            ("Fatiha Lkamel", "30967"),
            ("Abdelhamid Jaber", "30708"),
            ("Yassine Elkanouni", "30735")
        ]
        
        for agent_name, workspace_id in agents:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role) 
                VALUES (?, ?, ?)
            """, (agent_name, hash_password(workspace_id), "agent"))
        
        conn.commit()
    finally:
        conn.close()

def is_killswitch_enabled():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT killswitch_enabled FROM system_settings WHERE id = 1")
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def is_chat_killswitch_enabled():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_killswitch_enabled FROM system_settings WHERE id = 1")
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def toggle_killswitch(enable):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_settings SET killswitch_enabled = ? WHERE id = 1",
                      (1 if enable else 0,))
        conn.commit()
        return True
    finally:
        conn.close()

def toggle_chat_killswitch(enable):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_settings SET chat_killswitch_enabled = ? WHERE id = 1",
                      (1 if enable else 0,))
        conn.commit()
        return True
    finally:
        conn.close()

def add_request(agent_name, request_type, identifier, comment):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO requests (agent_name, request_type, identifier, comment, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, request_type, identifier, comment, timestamp))
        
        request_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO request_comments (request_id, user, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (request_id, agent_name, f"Request created: {comment}", timestamp))
        
        conn.commit()
        return True
    finally:
        conn.close()

def get_requests():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_requests(query):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        query = f"%{query.lower()}%"
        cursor.execute("""
            SELECT * FROM requests 
            WHERE LOWER(agent_name) LIKE ? 
            OR LOWER(request_type) LIKE ? 
            OR LOWER(identifier) LIKE ? 
            OR LOWER(comment) LIKE ?
            ORDER BY timestamp DESC
        """, (query, query, query, query))
        return cursor.fetchall()
    finally:
        conn.close()

def update_request_status(request_id, completed):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE requests SET completed = ? WHERE id = ?",
                      (1 if completed else 0, request_id))
        conn.commit()
        return True
    finally:
        conn.close()

def add_request_comment(request_id, user, comment):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO request_comments (request_id, user, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (request_id, user, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_request_comments(request_id):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM request_comments 
            WHERE request_id = ?
            ORDER BY timestamp ASC
        """, (request_id,))
        return cursor.fetchall()
    finally:
        conn.close()

def add_mistake(team_leader, agent_name, ticket_id, error_description):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mistakes (team_leader, agent_name, ticket_id, error_description, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        """, (team_leader, agent_name, ticket_id, error_description,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_mistakes():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mistakes ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_mistakes(query):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        query = f"%{query.lower()}%"
        cursor.execute("""
            SELECT * FROM mistakes 
            WHERE LOWER(agent_name) LIKE ? 
            OR LOWER(ticket_id) LIKE ? 
            OR LOWER(error_description) LIKE ?
            ORDER BY timestamp DESC
        """, (query, query, query))
        return cursor.fetchall()
    finally:
        conn.close()

def send_group_message(sender, message):
    if is_killswitch_enabled() or is_chat_killswitch_enabled():
        st.error("Chat is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        mentions = re.findall(r'@(\w+)', message)
        cursor.execute("""
            INSERT INTO group_messages (sender, message, timestamp, mentions) 
            VALUES (?, ?, ?, ?)
        """, (sender, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             ','.join(mentions)))
        conn.commit()
        return True
    finally:
        conn.close()

def get_group_messages():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_messages ORDER BY timestamp DESC LIMIT 50")
        return cursor.fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
        return cursor.fetchall()
    finally:
        conn.close()

def add_user(username, password, role):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      (username, hash_password(password), role))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_user(user_id):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def add_hold_image(uploader, image_data):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hold_images (uploader, image_data, timestamp) 
            VALUES (?, ?, ?)
        """, (uploader, image_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_hold_images():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hold_images ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def clear_hold_images():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hold_images")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_requests():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM requests")
        cursor.execute("DELETE FROM request_comments")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_mistakes():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mistakes")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_group_messages():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_messages")
        conn.commit()
        return True
    finally:
        conn.close()

# --------------------------
# Break Scheduling Functions (from first code)
# --------------------------

def init_break_session_state():
    if 'templates' not in st.session_state:
        st.session_state.templates = {}
    if 'current_template' not in st.session_state:
        st.session_state.current_template = None
    if 'agent_bookings' not in st.session_state:
        st.session_state.agent_bookings = {}
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().strftime('%Y-%m-%d')
    if 'timezone_offset' not in st.session_state:
        st.session_state.timezone_offset = 0  # GMT by default
    if 'break_limits' not in st.session_state:
        st.session_state.break_limits = {}
    
    # Load data from files if exists
    if os.path.exists('templates.json'):
        with open('templates.json', 'r') as f:
            st.session_state.templates = json.load(f)
    if os.path.exists('break_limits.json'):
        with open('break_limits.json', 'r') as f:
            st.session_state.break_limits = json.load(f)
    if os.path.exists('all_bookings.json'):
        with open('all_bookings.json', 'r') as f:
            st.session_state.agent_bookings = json.load(f)

def save_break_data():
    with open('templates.json', 'w') as f:
        json.dump(st.session_state.templates, f)
    with open('break_limits.json', 'w') as f:
        json.dump(st.session_state.break_limits, f)
    with open('all_bookings.json', 'w') as f:
        json.dump(st.session_state.agent_bookings, f)

def adjust_time(time_str, offset):
    try:
        if not time_str.strip():
            return ""
        time_obj = datetime.strptime(time_str.strip(), "%H:%M")
        adjusted_time = (time_obj + timedelta(hours=offset)).time()
        return adjusted_time.strftime("%H:%M")
    except:
        return time_str

def adjust_template_times(template, offset):
    adjusted_template = {
        "lunch_breaks": [adjust_time(t, offset) for t in template["lunch_breaks"]],
        "tea_breaks": {
            "First": [adjust_time(t, offset) for t in template["tea_breaks"]["First"]],
            "late": [adjust_time(t, offset) for t in template["tea_breaks"]["late"]]
        }
    }
    return adjusted_template

def count_bookings(date, break_type, time_slot):
    count = 0
    if date in st.session_state.agent_bookings:
        for agent_id, breaks in st.session_state.agent_bookings[date].items():
            if break_type == "lunch" and "lunch" in breaks and breaks["lunch"] == time_slot:
                count += 1
            elif break_type == "First_tea" and "First_tea" in breaks and breaks["First_tea"] == time_slot:
                count += 1
            elif break_type == "late_tea" and "late_tea" in breaks and breaks["late_tea"] == time_slot:
                count += 1
    return count

def display_schedule(template):
    st.header("LM US ENG 3:00 PM shift")
    
    st.table(lunch_df)
    
    st.markdown("**KINDLY RESPECT THE RULES BELOW**")
    st.markdown("**Non Respect Of Break Rules = Incident**")
    st.markdown("---")
    
    # Tea breaks table
    
    
    # Create two columns for tea breaks
    max_rows = max(len(template["tea_breaks"]["First"]), len(template["tea_breaks"]["late"]))
    tea_data = {
        "TEA BREAK": template["tea_breaks"]["First"] + [""] * (max_rows - len(template["tea_breaks"]["First"])),
        "TEA BREAK": template["tea_breaks"]["late"] + [""] * (max_rows - len(template["tea_breaks"]["late"]))
    }
    tea_df = pd.DataFrame(tea_data)
    st.table(tea_df)
    
    # Rules section
    st.markdown("""
    **NO BREAK IN THE LAST HOUR WILL BE AUTHORIZED**  
    **PS: ONLY 5 MINUTES BIO IS AUTHORIZED IN THE LAST HOUR BETWEEN 23:00 TILL 23:30 AND NO BREAK AFTER 23:30 !!!**  
    **BREAKS SHOULD BE TAKEN AT THE NOTED TIME AND NEED TO BE CONFIRMED FROM RTA OR TEAM LEADERS**
    """)

def admin_break_dashboard():
    st.title("Admin Dashboard")
    st.markdown("---")
    
    # Timezone adjustment
    st.header("Timezone Adjustment")
    timezone = st.selectbox(
        "Select Timezone:", 
        ["GMT", "GMT+1", "GMT+2", "GMT-1", "GMT-2"],
        index=0
    )
    
    # Map timezone to offset
    timezone_offsets = {"GMT": 0, "GMT+1": 1, "GMT+2": 2, "GMT-1": -1, "GMT-2": -2}
    new_offset = timezone_offsets[timezone]
    
    if new_offset != st.session_state.timezone_offset:
        st.session_state.timezone_offset = new_offset
        st.success(f"Timezone set to {timezone}. All break times adjusted.")
        st.rerun()
    
    # Template management
    st.header("Template Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        template_name = st.text_input("Template Name:")
    
    with col2:
        if st.button("Create New Template"):
            if template_name:
                if template_name not in st.session_state.templates:
                    st.session_state.templates[template_name] = {
                        "lunch_breaks": ["19:30", "20:00", "20:30", "21:00", "21:30"],
                        "tea_breaks": {
                            "First": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
                            "First": ["21:45", "22:00", "22:15", "22:30"]
                        }
                    }
                    st.session_state.current_template = template_name
                    save_break_data()
                    st.success(f"Template '{template_name}' created!")
                else:
                    st.error("Template with this name already exists")
            else:
                st.error("Please enter a template name")
    
    # Template selection
    if st.session_state.templates:
        selected_template = st.selectbox(
            "Select Template to Edit:",
            list(st.session_state.templates.keys()),
            index=0 if not st.session_state.current_template else list(st.session_state.templates.keys()).index(st.session_state.current_template)
        )
        
        st.session_state.current_template = selected_template
        
        if st.button("Delete Template"):
            del st.session_state.templates[selected_template]
            st.session_state.current_template = None
            save_break_data()
            st.success(f"Template '{selected_template}' deleted!")
            st.rerun()

        
        # Edit template
        if st.session_state.current_template:
            template = st.session_state.templates[st.session_state.current_template]
            
            st.subheader("Edit Lunch Breaks")
            lunch_breaks = st.text_area(
                "Lunch Breaks (one per line):",
                "\n".join(template["lunch_breaks"]),
                height=150
            )
            
            st.subheader("Edit Tea Breaks")
            st.write("First Tea Breaks:")
            First_tea_breaks = st.text_area(
                "First Tea Breaks (one per line):",
                "\n".join(template["tea_breaks"]["First"]),
                height=150,
                key="First_tea"
            )
            
            st.write("Late Tea Breaks:")
            late_tea_breaks = st.text_area(
                "Late Tea Breaks (one per line):",
                "\n".join(template["tea_breaks"]["late"]),
                height=150,
                key="late_tea"
            )
            
            if st.button("Save Changes"):
                template["lunch_breaks"] = [t.strip() for t in lunch_breaks.split("\n") if t.strip()]
                template["tea_breaks"]["First"] = [t.strip() for t in First_tea_breaks.split("\n") if t.strip()]
                template["tea_breaks"]["late"] = [t.strip() for t in late_tea_breaks.split("\n") if t.strip()]
                save_break_data()
                st.success("Template updated successfully!")
    
    # Break limits management
    st.header("Break Limits Management")
    if st.session_state.current_template:
        template = st.session_state.templates[st.session_state.current_template]
        
        # Initialize limits if not exists
        if st.session_state.current_template not in st.session_state.break_limits:
            st.session_state.break_limits[st.session_state.current_template] = {
                "lunch": {time: 5 for time in template["lunch_breaks"]},
                "First_tea": {time: 3 for time in template["tea_breaks"]["First"]},
                "late_tea": {time: 3 for time in template["tea_breaks"]["late"]}
            }
        
        st.subheader("Lunch Break Limits")
        lunch_cols = st.columns(len(template["lunch_breaks"]))
        for i, time_slot in enumerate(template["lunch_breaks"]):
            with lunch_cols[i]:
                st.session_state.break_limits[st.session_state.current_template]["lunch"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=st.session_state.break_limits[st.session_state.current_template]["lunch"].get(time_slot, 5),
                    key=f"lunch_limit_{time_slot}"
                )
        
        st.subheader("First Tea Break Limits")
        First_tea_cols = st.columns(len(template["tea_breaks"]["First"]))
        for i, time_slot in enumerate(template["tea_breaks"]["First"]):
            with First_tea_cols[i]:
                st.session_state.break_limits[st.session_state.current_template]["First_tea"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=st.session_state.break_limits[st.session_state.current_template]["First_tea"].get(time_slot, 3),
                    key=f"First_tea_limit_{time_slot}"
                )
        
        st.subheader("Late Tea Break Limits")
        late_tea_cols = st.columns(len(template["tea_breaks"]["late"]))
        for i, time_slot in enumerate(template["tea_breaks"]["late"]):
            with late_tea_cols[i]:
                st.session_state.break_limits[st.session_state.current_template]["late_tea"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=st.session_state.break_limits[st.session_state.current_template]["late_tea"].get(time_slot, 3),
                    key=f"late_tea_limit_{time_slot}"
                )
        
        if st.button("Save Break Limits"):
            save_break_data()
            st.success("Break limits saved successfully!")
    
    # View all bookings
    st.header("All Bookings")
    if st.session_state.agent_bookings:
        # Convert to DataFrame for better display
        bookings_list = []
        for date, agents in st.session_state.agent_bookings.items():
            for agent_id, breaks in agents.items():
                bookings_list.append({
                    "Date": date,
                    "Agent ID": agent_id,
                    "Lunch Break": breaks.get("lunch", "-"),
                    "First Tea": breaks.get("First_tea", "-"),
                    "Late Tea": breaks.get("late_tea", "-")
                })
        
        bookings_df = pd.DataFrame(bookings_list)
        st.dataframe(bookings_df)
        
        # Export option
        if st.button("Export Bookings to CSV"):
            csv = bookings_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="break_bookings.csv",
                mime="text/csv"
            )
    else:
        st.write("No bookings yet.")

def agent_break_dashboard():
    st.title("Break Booking")
    st.markdown("---")
    
    # Use the logged-in username directly
    agent_id = st.session_state.username
    st.write(f"Booking breaks for: **{agent_id}**")
    
    # Date selection
    schedule_date = st.date_input("Select Date:", datetime.now())
    st.session_state.selected_date = schedule_date.strftime('%Y-%m-%d')
    
    # Use the first template (or create a default if none exists)
    if not st.session_state.templates:
        st.error("No break schedules available. Please contact admin.")
        return
    
    # Get the first template (we're removing the template selection)
    template_name = list(st.session_state.templates.keys())[0]
    template = adjust_template_times(st.session_state.templates[template_name], st.session_state.timezone_offset)
    
    # Booking section
    st.markdown("---")
    st.header("Available Break Slots")
    
    # Check if template has limits defined
    break_limits = st.session_state.break_limits.get(template_name, {})
    
    # Lunch break booking
    st.subheader("Lunch Break")
    if template["lunch_breaks"]:
        lunch_cols = st.columns(len(template["lunch_breaks"]))
        selected_lunch = None
        
        for i, time_slot in enumerate(template["lunch_breaks"]):
            with lunch_cols[i]:
                # Check if time slot is full
                current_bookings = count_bookings(st.session_state.selected_date, "lunch", time_slot)
                max_limit = break_limits.get("lunch", {}).get(time_slot, 5)
                
                if current_bookings >= max_limit:
                    st.button(f"{time_slot} (FULL)", key=f"lunch_{time_slot}", disabled=True, help="This slot is full")
                else:
                    if st.button(time_slot, key=f"lunch_{time_slot}"):
                        selected_lunch = time_slot
        
        if selected_lunch:
            if st.session_state.selected_date not in st.session_state.agent_bookings:
                st.session_state.agent_bookings[st.session_state.selected_date] = {}
            
            if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
                st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
            
            st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["lunch"] = selected_lunch
            save_break_data()
            st.success(f"Lunch break booked for {selected_lunch}")
            st.rerun()
    else:
        st.write("No lunch breaks available today.")
    
    # Tea break booking
    st.subheader("Tea Breaks")
    st.write("First Tea Breaks:")
    First_tea_cols = st.columns(len(template["tea_breaks"]["First"]))
    selected_First_tea = None
    
    for i, time_slot in enumerate(template["tea_breaks"]["First"]):
        with First_tea_cols[i]:
            # Check if time slot is full
            current_bookings = count_bookings(st.session_state.selected_date, "First_tea", time_slot)
            max_limit = break_limits.get("First_tea", {}).get(time_slot, 3)
            
            if current_bookings >= max_limit:
                st.button(f"{time_slot} (FULL)", key=f"First_tea_{time_slot}", disabled=True, help="This slot is full")
            else:
                if st.button(time_slot, key=f"First_tea_{time_slot}"):
                    selected_First_tea = time_slot
    
    if selected_First_tea:
        if st.session_state.selected_date not in st.session_state.agent_bookings:
            st.session_state.agent_bookings[st.session_state.selected_date] = {}
        
        if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
            st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
        
        st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["First_tea"] = selected_First_tea
        save_break_data()
        st.success(f"First tea break booked for {selected_First_tea}")
        st.rerun()
    
    st.write("Late Tea Breaks:")
    late_tea_cols = st.columns(len(template["tea_breaks"]["late"]))
    selected_late_tea = None
    
    for i, time_slot in enumerate(template["tea_breaks"]["late"]):
        with late_tea_cols[i]:
            # Check if time slot is full
            current_bookings = count_bookings(st.session_state.selected_date, "late_tea", time_slot)
            max_limit = break_limits.get("late_tea", {}).get(time_slot, 3)
            
            if current_bookings >= max_limit:
                st.button(f"{time_slot} (FULL)", key=f"late_tea_{time_slot}", disabled=True, help="This slot is full")
            else:
                if st.button(time_slot, key=f"late_tea_{time_slot}"):
                    selected_late_tea = time_slot
    
    if selected_late_tea:
        if st.session_state.selected_date not in st.session_state.agent_bookings:
            st.session_state.agent_bookings[st.session_state.selected_date] = {}
        
        if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
            st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
        
        st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["late_tea"] = selected_late_tea
        save_break_data()
        st.success(f"Late tea break booked for {selected_late_tea}")
        st.rerun()
    
    # Display current bookings
    if st.session_state.selected_date in st.session_state.agent_bookings and agent_id in st.session_state.agent_bookings[st.session_state.selected_date]:
        st.markdown("---")
        st.header("Your Current Bookings")
        bookings = st.session_state.agent_bookings[st.session_state.selected_date][agent_id]
        
        if "lunch" in bookings:
            st.write(f"**Lunch Break:** {bookings['lunch']}")
        if "First_tea" in bookings:
            st.write(f"**First Tea Break:** {bookings['First_tea']}")
        if "late_tea" in bookings:
            st.write(f"**Late Tea Break:** {bookings['late_tea']}")
        
        if st.button("Cancel All Bookings"):
            del st.session_state.agent_bookings[st.session_state.selected_date][agent_id]
            save_break_data()
            st.success("All bookings canceled for this date")
            st.rerun()
# --------------------------
# Streamlit App
# --------------------------

st.set_page_config(
    page_title="Request Management System",
    page_icon=":office:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to match the original styling
def inject_custom_css():
    st.markdown("""
    <style>
        .stApp {
            background-color: white;
        }
        .stMarkdown h1 {
            color: black;
            font-size: 24px;
            font-weight: bold;
        }
        .stMarkdown h2 {
            color: black;
            font-size: 20px;
            font-weight: bold;
            border-bottom: 1px solid black;
        }
        .stDataFrame {
            width: 100%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
            text-align: center;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .warning {
            color: red;
            font-weight: bold;
        }
        .break-option {
            padding: 5px;
            margin: 2px;
            border-radius: 3px;
            cursor: pointer;
        }
        .break-option:hover {
            background-color: #f0f0f0;
        }
        .selected-break {
            background-color: #4CAF50;
            color: white;
        }
        .full-break {
            background-color: #FF5252;
            color: white;
        }
        .stApp { background-color: #121212; color: #E0E0E0; }
        [data-testid="stSidebar"] { background-color: #1E1E1E; }
        .stButton>button { background-color: #2563EB; color: white; }
        .card { background-color: #1F1F1F; border-radius: 12px; padding: 1.5rem; }
        .metric-card { background-color: #1F2937; border-radius: 10px; padding: 20px; }
        .killswitch-active {
            background-color: #4A1E1E;
            border-left: 5px solid #D32F2F;
            padding: 1rem;
            margin-bottom: 1rem;
            color: #FFCDD2;
        }
        .chat-killswitch-active {
            background-color: #1E3A4A;
            border-left: 5px solid #1E88E5;
            padding: 1rem;
            margin-bottom: 1rem;
            color: #B3E5FC;
        }
        .comment-box {
            margin: 0.5rem 0;
            padding: 0.5rem;
            background: #2D2D2D;
            border-radius: 8px;
        }
        .comment-user {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.25rem;
        }
        .comment-text {
            margin-top: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.update({
        "authenticated": False,
        "role": None,
        "username": None,
        "current_section": "requests",
        "last_request_count": 0,
        "last_mistake_count": 0,
        "last_message_ids": []
    })

init_db()
init_break_session_state()

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 Request Management System")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if username and password:
                    role = authenticate(username, password)
                    if role:
                        st.session_state.update({
                            "authenticated": True,
                            "role": role,
                            "username": username,
                            "last_request_count": len(get_requests()),
                            "last_mistake_count": len(get_mistakes()),
                            "last_message_ids": [msg[0] for msg in get_group_messages()]
                        })
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

else:
    if is_killswitch_enabled():
        st.markdown("""
        <div class="killswitch-active">
            <h3>⚠️ SYSTEM LOCKED ⚠️</h3>
            <p>The system is currently in read-only mode.</p>
        </div>
        """, unsafe_allow_html=True)
    elif is_chat_killswitch_enabled():
        st.markdown("""
        <div class="chat-killswitch-active">
            <h3>⚠️ CHAT LOCKED ⚠️</h3>
            <p>The chat functionality is currently disabled.</p>
        </div>
        """, unsafe_allow_html=True)

    def show_notifications():
        current_requests = get_requests()
        current_mistakes = get_mistakes()
        current_messages = get_group_messages()
        
        new_requests = len(current_requests) - st.session_state.last_request_count
        if new_requests > 0 and st.session_state.last_request_count > 0:
            st.toast(f"📋 {new_requests} new request(s) submitted!")
        st.session_state.last_request_count = len(current_requests)
        
        new_mistakes = len(current_mistakes) - st.session_state.last_mistake_count
        if new_mistakes > 0 and st.session_state.last_mistake_count > 0:
            st.toast(f"❌ {new_mistakes} new mistake(s) reported!")
        st.session_state.last_mistake_count = len(current_mistakes)
        
        current_message_ids = [msg[0] for msg in current_messages]
        new_messages = [msg for msg in current_messages if msg[0] not in st.session_state.last_message_ids]
        for msg in new_messages:
            if msg[1] != st.session_state.username:
                mentions = msg[4].split(',') if msg[4] else []
                if st.session_state.username in mentions:
                    st.toast(f"💬 You were mentioned by {msg[1]}!")
                else:
                    st.toast(f"💬 New message from {msg[1]}!")
        st.session_state.last_message_ids = current_message_ids

    show_notifications()

    with st.sidebar:
        st.title(f"👋 Welcome, {st.session_state.username}")
        st.markdown("---")
        
        nav_options = [
            ("📋 Requests", "requests"),
            ("📊 Dashboard", "dashboard"),
            ("☕ Breaks", "breaks"),
            ("🖼️ HOLD", "hold"),
            ("❌ Mistakes", "mistakes"),
            ("💬 Chat", "chat")
        ]
        if st.session_state.role == "admin":
            nav_options.append(("⚙️ Admin", "admin"))
        
        for option, value in nav_options:
            if st.button(option, key=f"nav_{value}"):
                st.session_state.current_section = value
                
        st.markdown("---")
        pending_requests = len([r for r in get_requests() if not r[6]])
        new_mistakes = len(get_mistakes())
        unread_messages = len([m for m in get_group_messages() 
                             if m[0] not in st.session_state.last_message_ids 
                             and m[1] != st.session_state.username])
        
        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h4>🔔 Notifications</h4>
            <p>📋 Pending requests: {pending_requests}</p>
            <p>❌ Recent mistakes: {new_mistakes}</p>
            <p>💬 Unread messages: {unread_messages}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.rerun()

    st.title(st.session_state.current_section.title())

    if st.session_state.current_section == "requests":
        if not is_killswitch_enabled():
            with st.expander("➕ Submit New Request"):
                with st.form("request_form"):
                    cols = st.columns([1, 3])
                    request_type = cols[0].selectbox("Type", ["Email", "Phone", "Ticket"])
                    identifier = cols[1].text_input("Identifier")
                    comment = st.text_area("Comment")
                    if st.form_submit_button("Submit"):
                        if identifier and comment:
                            if add_request(st.session_state.username, request_type, identifier, comment):
                                st.success("Request submitted successfully!")
                                st.rerun()
        
        st.subheader("🔍 Search Requests")
        search_query = st.text_input("Search requests...")
        requests = search_requests(search_query) if search_query else get_requests()
        
        st.subheader("All Requests")
        for req in requests:
            req_id, agent, req_type, identifier, comment, timestamp, completed = req
            with st.container():
                cols = st.columns([0.1, 0.9])
                with cols[0]:
                    if not is_killswitch_enabled():
                        st.checkbox("Done", value=bool(completed), 
                                   key=f"check_{req_id}", 
                                   on_change=update_request_status,
                                   args=(req_id, not completed))
                    else:
                        st.checkbox("Done", value=bool(completed), disabled=True)
                with cols[1]:
                    st.markdown(f"""
                    <div class="card">
                        <div style="display: flex; justify-content: space-between;">
                            <h4>#{req_id} - {req_type}</h4>
                            <small>{timestamp}</small>
                        </div>
                        <p>Agent: {agent}</p>
                        <p>Identifier: {identifier}</p>
                        <div style="margin-top: 1rem;">
                            <h5>Status Updates:</h5>
                    """, unsafe_allow_html=True)
                    
                    comments = get_request_comments(req_id)
                    for comment in comments:
                        cmt_id, _, user, cmt_text, cmt_time = comment
                        st.markdown(f"""
                            <div class="comment-box">
                                <div class="comment-user">
                                    <small><strong>{user}</strong></small>
                                    <small>{cmt_time}</small>
                                </div>
                                <div class="comment-text">{cmt_text}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    if st.session_state.role == "admin" and not is_killswitch_enabled():
                        with st.form(key=f"comment_form_{req_id}"):
                            new_comment = st.text_input("Add status update/comment")
                            if st.form_submit_button("Add Comment"):
                                if new_comment:
                                    add_request_comment(req_id, st.session_state.username, new_comment)
                                    st.rerun()

    elif st.session_state.current_section == "dashboard":
        st.subheader("📊 Request Completion Dashboard")
        all_requests = get_requests()
        total = len(all_requests)
        completed = sum(1 for r in all_requests if r[6])
        rate = (completed/total*100) if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Requests", total)
        with col2:
            st.metric("Completed", completed)
        with col3:
            st.metric("Completion Rate", f"{rate:.1f}%")
        
        df = pd.DataFrame({
            'Date': [datetime.strptime(r[5], "%Y-%m-%d %H:%M:%S").date() for r in all_requests],
            'Status': ['Completed' if r[6] else 'Pending' for r in all_requests],
            'Type': [r[2] for r in all_requests]
        })
        
        st.subheader("Request Trends")
        st.bar_chart(df['Date'].value_counts())
        
        st.subheader("Request Type Distribution")
        type_counts = df['Type'].value_counts().reset_index()
        type_counts.columns = ['Type', 'Count']
        st.bar_chart(type_counts.set_index('Type'))

    elif st.session_state.current_section == "breaks":
        if st.session_state.role == "admin":
            admin_break_dashboard()
        else:
            agent_break_dashboard()

    elif st.session_state.current_section == "mistakes":
        if not is_killswitch_enabled():
            with st.expander("➕ Report New Mistake"):
                with st.form("mistake_form"):
                    cols = st.columns(3)
                    agent_name = cols[0].text_input("Agent Name")
                    ticket_id = cols[1].text_input("Ticket ID")
                    error_description = st.text_area("Error Description")
                    if st.form_submit_button("Submit"):
                        if agent_name and ticket_id and error_description:
                            add_mistake(st.session_state.username, agent_name, ticket_id, error_description)
        
        st.subheader("🔍 Search Mistakes")
        search_query = st.text_input("Search mistakes...")
        mistakes = search_mistakes(search_query) if search_query else get_mistakes()
        
        st.subheader("Mistakes Log")
        for mistake in mistakes:
            m_id, tl, agent, ticket, error, ts = mistake
            st.markdown(f"""
            <div class="card">
                <div style="display: flex; justify-content: space-between;">
                    <h4>#{m_id}</h4>
                    <small>{ts}</small>
                </div>
                <p>Agent: {agent}</p>
                <p>Ticket: {ticket}</p>
                <p>Error: {error}</p>
            </div>
            """, unsafe_allow_html=True)

    elif st.session_state.current_section == "chat":
        if is_chat_killswitch_enabled():
            st.warning("Chat functionality is currently disabled by the administrator.")
        else:
            messages = get_group_messages()
            for msg in reversed(messages):
                msg_id, sender, message, ts, mentions = msg
                is_mentioned = st.session_state.username in (mentions.split(',') if mentions else [])
                st.markdown(f"""
                <div style="background-color: {'#3b82f6' if is_mentioned else '#1F1F1F'};
                            padding: 1rem;
                            border-radius: 8px;
                            margin-bottom: 1rem;">
                    <strong>{sender}</strong>: {message}<br>
                    <small>{ts}</small>
                </div>
                """, unsafe_allow_html=True)
            
            if not is_killswitch_enabled():
                with st.form("chat_form"):
                    message = st.text_input("Type your message...")
                    if st.form_submit_button("Send"):
                        if message:
                            send_group_message(st.session_state.username, message)
                            st.rerun()

    elif st.session_state.current_section == "hold":
        if st.session_state.role == "admin" and not is_killswitch_enabled():
            with st.expander("📤 Upload Image"):
                img = st.file_uploader("Choose image", type=["jpg", "png", "jpeg"])
                if img:
                    add_hold_image(st.session_state.username, img.read())
        
        images = get_hold_images()
        if images:
            for img in images:
                iid, uploader, data, ts = img
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between;">
                        <h4>Image #{iid}</h4>
                        <small>{ts}</small>
                    </div>
                    <p>Uploaded by: {uploader}</p>
                </div>
                """, unsafe_allow_html=True)
                st.image(Image.open(io.BytesIO(data)), use_container_width=True)
        else:
            st.info("No images in HOLD")

    elif st.session_state.current_section == "admin" and st.session_state.role == "admin":
        if st.session_state.username.lower() == "taha kirri":
            st.subheader("🚨 System Killswitch")
            current = is_killswitch_enabled()
            status = "🔴 ACTIVE" if current else "🟢 INACTIVE"
            st.write(f"Current Status: {status}")
            
            col1, col2 = st.columns(2)
            if current:
                if col1.button("Deactivate Killswitch"):
                    toggle_killswitch(False)
                    st.rerun()
            else:
                if col1.button("Activate Killswitch"):
                    toggle_killswitch(True)
                    st.rerun()
            
            st.markdown("---")
            
            st.subheader("💬 Chat Killswitch")
            current_chat = is_chat_killswitch_enabled()
            chat_status = "🔴 ACTIVE" if current_chat else "🟢 INACTIVE"
            st.write(f"Current Status: {chat_status}")
            
            col1, col2 = st.columns(2)
            if current_chat:
                if col1.button("Deactivate Chat Killswitch"):
                    toggle_chat_killswitch(False)
                    st.rerun()
            else:
                if col1.button("Activate Chat Killswitch"):
                    toggle_chat_killswitch(True)
                    st.rerun()
            
            st.markdown("---")
        
        st.subheader("🧹 Data Management")
        
        with st.expander("❌ Clear All Requests"):
            with st.form("clear_requests_form"):
                st.warning("This will permanently delete ALL requests and their comments!")
                if st.form_submit_button("Clear All Requests"):
                    if clear_all_requests():
                        st.success("All requests deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Mistakes"):
            with st.form("clear_mistakes_form"):
                st.warning("This will permanently delete ALL mistakes!")
                if st.form_submit_button("Clear All Mistakes"):
                    if clear_all_mistakes():
                        st.success("All mistakes deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Chat Messages"):
            with st.form("clear_chat_form"):
                st.warning("This will permanently delete ALL chat messages!")
                if st.form_submit_button("Clear All Chat"):
                    if clear_all_group_messages():
                        st.success("All chat messages deleted!")
                        st.rerun()

        with st.expander("❌ Clear All HOLD Images"):
            with st.form("clear_hold_form"):
                st.warning("This will permanently delete ALL HOLD images!")
                if st.form_submit_button("Clear All HOLD Images"):
                    if clear_hold_images():
                        st.success("All HOLD images deleted!")
                        st.rerun()

        with st.expander("💣 Clear ALL Data"):
            with st.form("nuclear_form"):
                st.error("THIS WILL DELETE EVERYTHING IN THE SYSTEM!")
                if st.form_submit_button("🚨 Execute Full System Wipe"):
                    try:
                        clear_all_requests()
                        clear_all_mistakes()
                        clear_all_group_messages()
                        clear_hold_images()
                        st.success("All system data deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during deletion: {str(e)}")
        
        st.markdown("---")
        st.subheader("User Management")
        if not is_killswitch_enabled():
            with st.form("add_user"):
                user = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                role = st.selectbox("Role", ["agent", "admin"])
                if st.form_submit_button("Add User"):
                    if user and pwd:
                        add_user(user, pwd, role)
                        st.rerun()
        
        st.subheader("Existing Users")
        users = get_all_users()
        for uid, uname, urole in users:
            cols = st.columns([3, 1, 1])
            cols[0].write(uname)
            cols[1].write(urole)
            if cols[2].button("Delete", key=f"del_{uid}") and not is_killswitch_enabled():
                delete_user(uid)
                st.rerun()

if __name__ == "__main__":
    inject_custom_css()
    st.write("Request Management System")
