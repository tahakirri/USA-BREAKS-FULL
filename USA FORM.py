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

def get_db_connection():
    """Create and return a database connection."""
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect("data/requests.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    conn = get_db_connection()
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
    conn = get_db_connection()
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                user TEXT,
                comment TEXT,
                timestamp TEXT,
                FOREIGN KEY(request_id) REFERENCES requests(id))
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS late_logins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                presence_time TEXT,
                login_time TEXT,
                reason TEXT,
                timestamp TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                issue_type TEXT,
                timing TEXT,
                mobile_number TEXT,
                product TEXT,
                timestamp TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS midshift_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                issue_type TEXT,
                start_time TEXT,
                end_time TEXT,
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT killswitch_enabled FROM system_settings WHERE id = 1")
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def is_chat_killswitch_enabled():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_killswitch_enabled FROM system_settings WHERE id = 1")
        result = cursor.fetchone()
        return bool(result[0]) if result else False
    finally:
        conn.close()

def toggle_killswitch(enable):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE system_settings SET killswitch_enabled = ? WHERE id = 1",
                      (1 if enable else 0,))
        conn.commit()
        return True
    finally:
        conn.close()

def toggle_chat_killswitch(enable):
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_requests(query):
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mistakes ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_mistakes(query):
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_messages ORDER BY timestamp DESC LIMIT 50")
        return cursor.fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
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
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM group_messages")
        conn.commit()
        return True
    finally:
        conn.close()

def add_late_login(agent_name, presence_time, login_time, reason):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO late_logins (agent_name, presence_time, login_time, reason, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, presence_time, login_time, reason,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_late_logins():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM late_logins ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def add_quality_issue(agent_name, issue_type, timing, mobile_number, product):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO quality_issues (agent_name, issue_type, timing, mobile_number, product, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_name, issue_type, timing, mobile_number, product,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_quality_issues():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM quality_issues ORDER BY timestamp DESC")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching quality issues: {str(e)}")
    finally:
        conn.close()

def add_midshift_issue(agent_name, issue_type, start_time, end_time):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO midshift_issues (agent_name, issue_type, start_time, end_time, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, issue_type, start_time, end_time,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding mid-shift issue: {str(e)}")
    finally:
        conn.close()

def get_midshift_issues():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM midshift_issues ORDER BY timestamp DESC")
        return cursor.fetchall()
    except Exception as e:
        st.error(f"Error fetching mid-shift issues: {str(e)}")
    finally:
        conn.close()

def clear_late_logins():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM late_logins")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error clearing late logins: {str(e)}")
    finally:
        conn.close()

def clear_quality_issues():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quality_issues")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error clearing quality issues: {str(e)}")
    finally:
        conn.close()

def clear_midshift_issues():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM midshift_issues")
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error clearing mid-shift issues: {str(e)}")
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
    if 'active_templates' not in st.session_state:
        st.session_state.active_templates = []
    
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
    if os.path.exists('active_templates.json'):
        with open('active_templates.json', 'r') as f:
            st.session_state.active_templates = json.load(f)

def save_break_data():
    with open('templates.json', 'w') as f:
        json.dump(st.session_state.templates, f)
    with open('break_limits.json', 'w') as f:
        json.dump(st.session_state.break_limits, f)
    with open('all_bookings.json', 'w') as f:
        json.dump(st.session_state.agent_bookings, f)
    with open('active_templates.json', 'w') as f:
        json.dump(st.session_state.active_templates, f)

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
    """Safely adjust template times with proper error handling"""
    try:
        if not template or not isinstance(template, dict):
            return {
                "lunch_breaks": [],
                "tea_breaks": {"early": [], "late": []}
            }
            
        adjusted_template = {
            "lunch_breaks": [adjust_time(t, offset) for t in template.get("lunch_breaks", [])],
            "tea_breaks": {
                "early": [adjust_time(t, offset) for t in template.get("tea_breaks", {}).get("early", [])],
                "late": [adjust_time(t, offset) for t in template.get("tea_breaks", {}).get("late", [])]
            }
        }
        return adjusted_template
    except Exception as e:
        st.error(f"Error adjusting template times: {str(e)}")
        return {
            "lunch_breaks": [],
            "tea_breaks": {"early": [], "late": []}
        }

def count_bookings(date, break_type, time_slot):
    count = 0
    if date in st.session_state.agent_bookings:
        for agent_id, breaks in st.session_state.agent_bookings[date].items():
            if break_type == "lunch" and "lunch" in breaks and breaks["lunch"] == time_slot:
                count += 1
            elif break_type == "early_tea" and "early_tea" in breaks and breaks["early_tea"] == time_slot:
                count += 1
            elif break_type == "late_tea" and "late_tea" in breaks and breaks["late_tea"] == time_slot:
                count += 1
    return count

def display_schedule(template):
    st.header("LM US ENG 3:00 PM shift")
    
    # Lunch breaks table
    st.markdown("### LUNCH BREAKS")
    lunch_df = pd.DataFrame({
        "DATE": [st.session_state.selected_date],
        **{time: [""] for time in template["lunch_breaks"]}
    })
    st.table(lunch_df)
    
    st.markdown("**KINDLY RESPECT THE RULES BELOW**")
    st.markdown("**Non Respect Of Break Rules = Incident**")
    st.markdown("---")
    
    # Tea breaks table
    st.markdown("### TEA BREAK")
    
    # Create two columns for tea breaks
    max_rows = max(len(template["tea_breaks"]["early"]), len(template["tea_breaks"]["late"]))
    tea_data = {
        "TEA BREAK": template["tea_breaks"]["early"] + [""] * (max_rows - len(template["tea_breaks"]["early"])),
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

def migrate_booking_data():
    if 'agent_bookings' in st.session_state:
        for date in st.session_state.agent_bookings:
            for agent in st.session_state.agent_bookings[date]:
                bookings = st.session_state.agent_bookings[date][agent]
                if "lunch" in bookings and isinstance(bookings["lunch"], str):
                    bookings["lunch"] = {
                        "time": bookings["lunch"],
                        "template": "Default Template",
                        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                if "early_tea" in bookings and isinstance(bookings["early_tea"], str):
                    bookings["early_tea"] = {
                        "time": bookings["early_tea"],
                        "template": "Default Template",
                        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                if "late_tea" in bookings and isinstance(bookings["late_tea"], str):
                    bookings["late_tea"] = {
                        "time": bookings["late_tea"],
                        "template": "Default Template",
                        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
        
        save_break_data()

def clear_all_bookings():
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
    
    st.session_state.agent_bookings = {}
    save_break_data()
    return True

def adjust_template_time(time_str, hours):
    """Adjust a single time string by adding/subtracting hours"""
    try:
        if not time_str.strip():
            return ""
        time_obj = datetime.strptime(time_str.strip(), "%H:%M")
        adjusted_time = (time_obj + timedelta(hours=hours)).time()
        return adjusted_time.strftime("%H:%M")
    except:
        return time_str

def bulk_update_template_times(hours):
    """Update all template times by adding/subtracting hours"""
    if 'templates' not in st.session_state:
        return False
    
    try:
        for template_name in st.session_state.templates:
            template = st.session_state.templates[template_name]
            
            # Update lunch breaks
            template["lunch_breaks"] = [
                adjust_template_time(t, hours) 
                for t in template["lunch_breaks"]
            ]
            
            # Update early tea breaks
            template["tea_breaks"]["early"] = [
                adjust_template_time(t, hours) 
                for t in template["tea_breaks"]["early"]
            ]
            
            # Update late tea breaks
            template["tea_breaks"]["late"] = [
                adjust_template_time(t, hours) 
                for t in template["tea_breaks"]["late"]
            ]
        
        save_break_data()
        return True
    except Exception as e:
        st.error(f"Error updating template times: {str(e)}")
        return False

def admin_break_dashboard():
    st.title("Admin Dashboard")
    st.markdown("---")
    
    # Bulk Time Update
    st.header("Bulk Time Update")
    st.warning("⚠️ This will permanently update all time slots in all templates!")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➕ Add 1 Hour to All Times"):
            if bulk_update_template_times(1):
                st.success("Successfully added 1 hour to all template times!")
                st.rerun()
    
    with col2:
        if st.button("➖ Subtract 1 Hour from All Times"):
            if bulk_update_template_times(-1):
                st.success("Successfully subtracted 1 hour from all template times!")
                st.rerun()
    
    # Clear All Bookings button
    st.header("Clear All Bookings")
    if st.button("Clear All Break Bookings"):
        if clear_all_bookings():
            st.success("All break bookings have been cleared!")
            st.rerun()
    
    # Template management
    st.header("Template Management")
    
    # Initialize templates if empty
    if 'templates' not in st.session_state:
        st.session_state.templates = {}
    
    # Create default template if no templates exist
    if not st.session_state.templates:
        default_template = {
            "lunch_breaks": ["19:30", "20:00", "20:30", "21:00", "21:30"],
            "tea_breaks": {
                "early": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
                "late": ["21:45", "22:00", "22:15", "22:30"]
            }
        }
        st.session_state.templates["Default Template"] = default_template
        st.session_state.current_template = "Default Template"
        if "Default Template" not in st.session_state.active_templates:
            st.session_state.active_templates.append("Default Template")
        save_break_data()
    
    # Active Templates Management
    st.subheader("Active Templates")
    st.write("Select which templates agents can book from:")
    
    for template_name in st.session_state.templates.keys():
        is_active = template_name in st.session_state.active_templates
        if st.checkbox(f"Active: {template_name}", value=is_active, key=f"active_{template_name}"):
            if template_name not in st.session_state.active_templates:
                st.session_state.active_templates.append(template_name)
                save_break_data()
        else:
            if template_name in st.session_state.active_templates:
                st.session_state.active_templates.remove(template_name)
                save_break_data()
    
    st.markdown("---")
    
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
                            "early": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
                            "late": ["21:45", "22:00", "22:15", "22:30"]
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
            index=list(st.session_state.templates.keys()).index(st.session_state.current_template) if st.session_state.current_template else 0
        )
        
        st.session_state.current_template = selected_template
        template = st.session_state.templates[selected_template]
        
        if st.button("Delete Template"):
            if len(st.session_state.templates) > 1:  # Prevent deleting the last template
                del st.session_state.templates[selected_template]
                if selected_template in st.session_state.active_templates:
                    st.session_state.active_templates.remove(selected_template)
                st.session_state.current_template = list(st.session_state.templates.keys())[0]
                save_break_data()
                st.success(f"Template '{selected_template}' deleted!")
                st.rerun()
        
        # Edit template
        st.subheader("Edit Lunch Breaks")
        lunch_breaks = st.text_area(
            "Lunch Breaks (one per line):",
            "\n".join(template["lunch_breaks"]),
            height=150
        )
        
        st.subheader("Edit Tea Breaks")
        st.write("Early Tea Breaks:")
        early_tea_breaks = st.text_area(
            "Early Tea Breaks (one per line):",
            "\n".join(template["tea_breaks"]["early"]),
            height=150,
            key="early_tea"
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
            template["tea_breaks"]["early"] = [t.strip() for t in early_tea_breaks.split("\n") if t.strip()]
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
                "early_tea": {time: 3 for time in template["tea_breaks"]["early"]},
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
        
        st.subheader("Early Tea Break Limits")
        early_tea_cols = st.columns(len(template["tea_breaks"]["early"]))
        for i, time_slot in enumerate(template["tea_breaks"]["early"]):
            with early_tea_cols[i]:
                st.session_state.break_limits[st.session_state.current_template]["early_tea"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=st.session_state.break_limits[st.session_state.current_template]["early_tea"].get(time_slot, 3),
                    key=f"early_tea_limit_{time_slot}"
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
        # Migrate old data format if needed
        migrate_booking_data()
        
        # Add date filter
        dates = list(st.session_state.agent_bookings.keys())
        selected_date = st.selectbox("Select Date:", dates, index=len(dates)-1 if dates else 0)
        
        # Convert to DataFrame for better display
        bookings_list = []
        for date, agents in st.session_state.agent_bookings.items():
            if date == selected_date:  # Only show bookings for selected date
                for agent_id, breaks in agents.items():
                    # Find which template this agent is using
                    agent_template = None
                    for break_type in ['lunch', 'early_tea', 'late_tea']:
                        if break_type in breaks and isinstance(breaks[break_type], dict):
                            agent_template = breaks[break_type].get('template', 'Default Template')
                            break
                    
                    booking_entry = {
                        "Date": date,
                        "Agent": agent_id,
                        "Template": agent_template or "Default Template",
                        "Lunch": "-",
                        "Early Tea": "-",
                        "Late Tea": "-",
                        "Booked At": "-"
                    }
                    
                    # Add break times without template info
                    if "lunch" in breaks:
                        if isinstance(breaks["lunch"], dict):
                            booking_entry["Lunch"] = breaks["lunch"].get("time", "-")
                            booking_entry["Booked At"] = breaks["lunch"].get("booked_at", "N/A")
                        else:
                            booking_entry["Lunch"] = str(breaks["lunch"])
                    
                    if "early_tea" in breaks:
                        if isinstance(breaks["early_tea"], dict):
                            booking_entry["Early Tea"] = breaks["early_tea"].get("time", "-")
                            if booking_entry["Booked At"] == "-":
                                booking_entry["Booked At"] = breaks["early_tea"].get("booked_at", "N/A")
                        else:
                            booking_entry["Early Tea"] = str(breaks["early_tea"])
                    
                    if "late_tea" in breaks:
                        if isinstance(breaks["late_tea"], dict):
                            booking_entry["Late Tea"] = breaks["late_tea"].get("time", "-")
                            if booking_entry["Booked At"] == "-":
                                booking_entry["Booked At"] = breaks["late_tea"].get("booked_at", "N/A")
                        else:
                            booking_entry["Late Tea"] = str(breaks["late_tea"])
                    
                    bookings_list.append(booking_entry)
        
        if bookings_list:
            bookings_df = pd.DataFrame(bookings_list)
            st.dataframe(bookings_df)
            
            # Export option
            if st.button("Export Bookings to CSV"):
                csv = bookings_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"break_bookings_{selected_date}.csv",
                    mime="text/csv"
                )
        else:
            st.info(f"No bookings found for {selected_date}")
    else:
        st.write("No bookings yet.")

def agent_break_dashboard():
    if is_killswitch_enabled():
        st.error("System is currently locked. Break booking is disabled.")
        return
        
    st.title("Break Booking")
    st.markdown("---")
    
    # Initialize session state variables if they don't exist
    if 'agent_bookings' not in st.session_state:
        st.session_state.agent_bookings = {}
    
    if 'templates' not in st.session_state:
        st.session_state.templates = {}
    
    if 'selected_template_for_booking' not in st.session_state:
        st.session_state.selected_template_for_booking = None
        
    # Create default template if no templates exist
    if not st.session_state.templates:
        default_template = {
            "lunch_breaks": ["19:30", "20:00", "20:30", "21:00", "21:30"],
            "tea_breaks": {
                "early": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
                "late": ["21:45", "22:00", "22:15", "22:30"]
            }
        }
        st.session_state.templates["Default Template"] = default_template
        if "Default Template" not in st.session_state.active_templates:
            st.session_state.active_templates.append("Default Template")
    
    # Use the logged-in username directly
    agent_id = st.session_state.username
    st.write(f"Booking breaks for: **{agent_id}**")
    
    # Set date to current date only
    current_date = datetime.now()
    st.session_state.selected_date = current_date.strftime('%Y-%m-%d')
    st.write(f"**Current Date:** {st.session_state.selected_date}")
    
    # Check if there are any active templates
    if not st.session_state.active_templates:
        st.error("No active break schedules available. Please contact admin.")
        return
    
    try:
        # Get the agent's current template for today (if any)
        current_agent_template = None
        if (st.session_state.selected_date in st.session_state.agent_bookings and 
            agent_id in st.session_state.agent_bookings[st.session_state.selected_date]):
            bookings = st.session_state.agent_bookings[st.session_state.selected_date][agent_id]
            for break_type in ['lunch', 'early_tea', 'late_tea']:
                if break_type in bookings and isinstance(bookings[break_type], dict):
                    current_agent_template = bookings[break_type]['template']
                    break
        
        # Template selection section
        st.markdown("### 1. Select Your Break Schedule")
        if current_agent_template:
            st.info(f"You are currently using the **{current_agent_template}** template for today's breaks.")
            template_name = current_agent_template
            st.session_state.selected_template_for_booking = template_name
        else:
            template_name = st.selectbox(
                "First, select your break schedule template:",
                st.session_state.active_templates,
                key="template_selector",
                index=None,
                placeholder="Choose a template..."
            )
            if template_name:
                st.session_state.selected_template_for_booking = template_name
                st.success(f"You selected the **{template_name}** template. You can now book your breaks below.")
            else:
                st.warning("⚠️ Please select a break schedule template before booking any breaks.")
                return  # Stop here if no template is selected
        
        template = st.session_state.templates[template_name]
        
        if not template["lunch_breaks"] and not template["tea_breaks"]["early"] and not template["tea_breaks"]["late"]:
            st.error("Template appears to be empty or invalid. Please contact admin.")
            return
            
        # Check if template has limits defined
        break_limits = st.session_state.break_limits.get(template_name, {})
        
        # Booking section
        st.markdown("---")
        st.markdown("### 2. Available Break Slots")
        
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
                if is_killswitch_enabled():
                    st.error("System is locked. Cannot book breaks.")
                else:
                    if st.session_state.selected_date not in st.session_state.agent_bookings:
                        st.session_state.agent_bookings[st.session_state.selected_date] = {}
                    
                    if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
                        st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
                    
                    st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["lunch"] = {
                        "time": selected_lunch,
                        "template": template_name,
                        "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_break_data()
                    st.success(f"Lunch break booked for {selected_lunch}")
                    st.rerun()
        else:
            st.write("No lunch breaks available today.")
        
        # Tea break booking
        st.subheader("Tea Breaks")
        st.write("Early Tea Breaks:")
        early_tea_cols = st.columns(len(template["tea_breaks"]["early"]))
        selected_early_tea = None
        
        for i, time_slot in enumerate(template["tea_breaks"]["early"]):
            with early_tea_cols[i]:
                # Check if time slot is full
                current_bookings = count_bookings(st.session_state.selected_date, "early_tea", time_slot)
                max_limit = break_limits.get("early_tea", {}).get(time_slot, 3)
                
                if current_bookings >= max_limit:
                    st.button(f"{time_slot} (FULL)", key=f"early_tea_{time_slot}", disabled=True, help="This slot is full")
                else:
                    if st.button(time_slot, key=f"early_tea_{time_slot}"):
                        selected_early_tea = time_slot
        
        if selected_early_tea:
            if is_killswitch_enabled():
                st.error("System is locked. Cannot book breaks.")
            else:
                if st.session_state.selected_date not in st.session_state.agent_bookings:
                    st.session_state.agent_bookings[st.session_state.selected_date] = {}
                
                if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
                    st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
                
                st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["early_tea"] = {
                    "time": selected_early_tea,
                    "template": template_name,
                    "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_break_data()
                st.success(f"Early tea break booked for {selected_early_tea}")
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
            if is_killswitch_enabled():
                st.error("System is locked. Cannot book breaks.")
            else:
                if st.session_state.selected_date not in st.session_state.agent_bookings:
                    st.session_state.agent_bookings[st.session_state.selected_date] = {}
                
                if agent_id not in st.session_state.agent_bookings[st.session_state.selected_date]:
                    st.session_state.agent_bookings[st.session_state.selected_date][agent_id] = {}
                
                st.session_state.agent_bookings[st.session_state.selected_date][agent_id]["late_tea"] = {
                    "time": selected_late_tea,
                    "template": template_name,
                    "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_break_data()
                st.success(f"Late tea break booked for {selected_late_tea}")
                st.rerun()
        
        # Display current bookings
        if hasattr(st.session_state, 'selected_date') and hasattr(st.session_state, 'agent_bookings'):
            if (st.session_state.selected_date in st.session_state.agent_bookings and 
                agent_id in st.session_state.agent_bookings[st.session_state.selected_date]):
                
                # Migrate old data format if needed
                migrate_booking_data()
                
                st.markdown("---")
                st.header("Your Current Bookings")
                bookings = st.session_state.agent_bookings[st.session_state.selected_date][agent_id]
                
                if "lunch" in bookings:
                    if isinstance(bookings["lunch"], dict):
                        st.write(f"**Lunch Break:** {bookings['lunch']['time']} (Template: {bookings['lunch']['template']})")
                    else:
                        st.write(f"**Lunch Break:** {bookings['lunch']} (Template: Default Template)")
                
                if "early_tea" in bookings:
                    if isinstance(bookings["early_tea"], dict):
                        st.write(f"**Early Tea Break:** {bookings['early_tea']['time']} (Template: {bookings['early_tea']['template']})")
                    else:
                        st.write(f"**Early Tea Break:** {bookings['early_tea']} (Template: Default Template)")
                
                if "late_tea" in bookings:
                    if isinstance(bookings["late_tea"], dict):
                        st.write(f"**Late Tea Break:** {bookings['late_tea']['time']} (Template: {bookings['late_tea']['template']})")
                    else:
                        st.write(f"**Late Tea Break:** {bookings['late_tea']} (Template: Default Template)")
                
                if st.button("Cancel All Bookings"):
                    if is_killswitch_enabled():
                        st.error("System is locked. Cannot modify bookings.")
                    else:
                        del st.session_state.agent_bookings[st.session_state.selected_date][agent_id]
                        save_break_data()
                        st.success("All bookings canceled for this date")
                        st.rerun()
    except Exception as e:
        st.error(f"Error loading break schedule: {str(e)}")
        return

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
        /* Global Styles */
        .stApp {
            background-color: #f8fafc;
            color: #1e293b;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
            padding: 2rem 1rem;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            text-align: left;
            padding: 0.75rem 1rem;
            background-color: transparent;
            color: #475569;
            border: none;
            border-radius: 0.5rem;
            margin-bottom: 0.5rem;
            transition: all 0.2s;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background-color: #f1f5f9;
            color: #2563eb;
        }
        
        /* Card Styling */
        .card {
            background-color: #ffffff;
            border-radius: 1rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border: 1px solid #e2e8f0;
        }
        
        /* Form Styling */
        .stTextInput > div > div {
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
        }
        
        .stTextInput > div > div:focus-within {
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .stSelectbox > div > div {
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
        }
        
        /* Button Styling */
        .stButton > button {
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            background-color: #2563eb;
            color: white;
            border: none;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .stButton > button:hover {
            background-color: #1d4ed8;
            transform: translateY(-1px);
        }
        
        /* Login Form Styling */
        .login-container {
            max-width: 400px;
            margin: 4rem auto;
            padding: 2rem;
            background-color: white;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Notification Styling */
        .notification {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .notification.info {
            background-color: #dbeafe;
            color: #1e40af;
            border-left: 4px solid #2563eb;
        }
        
        .notification.warning {
            background-color: #fef3c7;
            color: #92400e;
            border-left: 4px solid #d97706;
        }
        
        .notification.error {
            background-color: #fee2e2;
            color: #991b1b;
            border-left: 4px solid #dc2626;
        }
        
        /* Comment Box Styling */
        .comment-box {
            background-color: #f8fafc;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
            border: 1px solid #e2e8f0;
        }
        
        .comment-user {
            display: flex;
            justify-content: space-between;
            color: #64748b;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }
        
        .comment-text {
            color: #334155;
        }
        
        /* Metric Card Styling */
        .metric-card {
            background-color: #ffffff;
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 600;
            color: #2563eb;
            margin: 0.5rem 0;
        }
        
        .metric-label {
            color: #64748b;
            font-size: 0.875rem;
        }
        
        /* Table Styling */
        .stDataFrame {
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            overflow: hidden;
        }
        
        .stDataFrame table {
            border-collapse: separate;
            border-spacing: 0;
        }
        
        .stDataFrame th {
            background-color: #f8fafc;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e2e8f0;
            color: #475569;
            font-weight: 500;
        }
        
        .stDataFrame td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #e2e8f0;
            color: #334155;
        }
        
        /* Killswitch Styling */
        .killswitch-active {
            background-color: #fee2e2;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid #dc2626;
            color: #991b1b;
        }
        
        .chat-killswitch-active {
            background-color: #dbeafe;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid #2563eb;
            color: #1e40af;
        }
        
        /* Header Styling */
        h1, h2, h3, h4, h5, h6 {
            color: #1e293b;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #f8fafc;
            border-radius: 0.5rem;
            border: 1px solid #e2e8f0;
            padding: 0.75rem 1rem;
            color: #475569;
            font-weight: 500;
        }
        
        /* Progress Bar Styling */
        .stProgress > div > div {
            background-color: #2563eb;
            border-radius: 1rem;
        }
        
        /* File Uploader Styling */
        .stFileUploader > div {
            border-radius: 0.5rem;
            border: 2px dashed #e2e8f0;
            padding: 2rem;
            text-align: center;
        }
        
        .stFileUploader > div:hover {
            border-color: #2563eb;
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
    st.markdown("""
        <div class="login-container">
            <h1 style="text-align: center; margin-bottom: 2rem;">🏢 Request Management System</h1>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
        with submit_col2:
            if st.form_submit_button("Login", use_container_width=True):
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
    
    st.markdown("</div>", unsafe_allow_html=True)

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
            ("💬 Chat", "chat"),
            ("📱 Fancy Number", "fancy_number"),
            ("⏰ Late Login", "late_login"),
            ("📞 Quality Issues", "quality_issues"),
            ("🔄 Mid-shift Issues", "midshift_issues")
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

    elif st.session_state.current_section == "fancy_number":
        st.title("📱 Fancy Number Checker")
        
        with st.form("fancy_number_form"):
            phone_number = st.text_input("Enter Phone Number", placeholder="Enter a 10-digit phone number")
            submit = st.form_submit_button("Check Number")
            
            if submit and phone_number:
                # Clean the phone number
                cleaned_number = ''.join(filter(str.isdigit, phone_number))
                
                if len(cleaned_number) != 10:
                    st.error("Please enter a valid 10-digit phone number")
                else:
                    # Check for patterns
                    patterns = []
                    
                    # Check for repeating digits
                    for i in range(10):
                        if str(i) * 3 in cleaned_number:
                            patterns.append(f"Contains triple {i}'s")
                        if str(i) * 4 in cleaned_number:
                            patterns.append(f"Contains quadruple {i}'s")
                    
                    # Check for sequential numbers (ascending and descending)
                    for i in range(len(cleaned_number)-2):
                        if (int(cleaned_number[i]) + 1 == int(cleaned_number[i+1]) and 
                            int(cleaned_number[i+1]) + 1 == int(cleaned_number[i+2])):
                            patterns.append("Contains ascending sequence")
                        elif (int(cleaned_number[i]) - 1 == int(cleaned_number[i+1]) and 
                              int(cleaned_number[i+1]) - 1 == int(cleaned_number[i+2])):
                            patterns.append("Contains descending sequence")
                    
                    # Check for palindrome patterns
                    for i in range(len(cleaned_number)-3):
                        segment = cleaned_number[i:i+4]
                        if segment == segment[::-1]:
                            patterns.append(f"Contains palindrome pattern: {segment}")
                    
                    # Check for repeated pairs
                    for i in range(len(cleaned_number)-1):
                        pair = cleaned_number[i:i+2]
                        if cleaned_number.count(pair) > 1:
                            patterns.append(f"Contains repeated pair: {pair}")
                    
                    # Format number in a readable way
                    formatted_number = f"({cleaned_number[:3]}) {cleaned_number[3:6]}-{cleaned_number[6:]}"
                    
                    # Display results
                    st.write("### Analysis Results")
                    st.write(f"Formatted Number: {formatted_number}")
                    
                    if patterns:
                        st.success("This is a fancy number! 🌟")
                        st.write("Special patterns found:")
                        for pattern in set(patterns):  # Using set to remove duplicates
                            st.write(f"- {pattern}")
                    else:
                        st.info("This appears to be a regular number. No special patterns found.")

    elif st.session_state.current_section == "late_login":
        st.subheader("⏰ Late Login Report")
        
        if not is_killswitch_enabled():
            with st.form("late_login_form"):
                cols = st.columns(3)
                presence_time = cols[0].text_input("Time of presence (HH:MM)", placeholder="08:30")
                login_time = cols[1].text_input("Time of log in (HH:MM)", placeholder="09:15")
                reason = cols[2].selectbox("Reason", [
                    "Workspace Issue",
                    "Avaya Issue",
                    "Aaad Tool",
                    "Windows Issue",
                    "Reset Password"
                ])
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(presence_time, "%H:%M")
                        datetime.strptime(login_time, "%H:%M")
                        add_late_login(
                            st.session_state.username,
                            presence_time,
                            login_time,
                            reason
                        )
                        st.success("Late login reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 08:30)")
        
        st.subheader("Late Login Records")
        late_logins = get_late_logins()
        
        if st.session_state.role == "admin":
            if late_logins:
                data = []
                for login in late_logins:
                    _, agent, presence, login_time, reason, ts = login
                    data.append({
                        "Agent's Name": agent,
                        "Time of presence": presence,
                        "Time of log in": login_time,
                        "Reason": reason
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="late_logins.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_late_logins()
                    st.rerun()
            else:
                st.info("No late login records found")
        else:
            user_logins = [login for login in late_logins if login[1] == st.session_state.username]
            if user_logins:
                data = []
                for login in user_logins:
                    _, agent, presence, login_time, reason, ts = login
                    data.append({
                        "Agent's Name": agent,
                        "Time of presence": presence,
                        "Time of log in": login_time,
                        "Reason": reason
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no late login records")

    elif st.session_state.current_section == "quality_issues":
        st.subheader("📞 Quality Related Technical Issue")
        
        if not is_killswitch_enabled():
            with st.form("quality_issue_form"):
                cols = st.columns(4)
                issue_type = cols[0].selectbox("Type of issue", [
                    "Blocage Physical Avaya",
                    "Hold Than Call Drop",
                    "Call Drop From Workspace",
                    "Wrong Space Frozen"
                ])
                timing = cols[1].text_input("Timing (HH:MM)", placeholder="14:30")
                mobile_number = cols[2].text_input("Mobile number")
                product = cols[3].selectbox("Product", [
                    "LM_CS_LMUSA_EN",
                    "LM_CS_LMUSA_ES"
                ])
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(timing, "%H:%M")
                        add_quality_issue(
                            st.session_state.username,
                            issue_type,
                            timing,
                            mobile_number,
                            product
                        )
                        st.success("Quality issue reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 14:30)")
        
        st.subheader("Quality Issue Records")
        quality_issues = get_quality_issues()
        
        if st.session_state.role == "admin":
            if quality_issues:
                data = []
                for issue in quality_issues:
                    _, agent, issue_type, timing, mobile, product, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Type of issue": issue_type,
                        "Timing": timing,
                        "Mobile number": mobile,
                        "Product": product
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="quality_issues.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_quality_issues()
                    st.rerun()
            else:
                st.info("No quality issue records found")
        else:
            user_issues = [issue for issue in quality_issues if issue[1] == st.session_state.username]
            if user_issues:
                data = []
                for issue in user_issues:
                    _, agent, issue_type, timing, mobile, product, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Type of issue": issue_type,
                        "Timing": timing,
                        "Mobile number": mobile,
                        "Product": product
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no quality issue records")

    elif st.session_state.current_section == "midshift_issues":
        st.subheader("🔄 Mid-shift Technical Issue")
        
        if not is_killswitch_enabled():
            with st.form("midshift_issue_form"):
                cols = st.columns(3)
                issue_type = cols[0].selectbox("Issue Type", [
                    "Default Not Ready",
                    "Frozen Workspace",
                    "Physical Avaya",
                    "Pc Issue",
                    "Aaad Tool",
                    "Disconnected Avaya"
                ])
                start_time = cols[1].text_input("Start time (HH:MM)", placeholder="10:00")
                end_time = cols[2].text_input("End time (HH:MM)", placeholder="10:30")
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(start_time, "%H:%M")
                        datetime.strptime(end_time, "%H:%M")
                        add_midshift_issue(
                            st.session_state.username,
                            issue_type,
                            start_time,
                            end_time
                        )
                        st.success("Mid-shift issue reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 10:00)")
        
        st.subheader("Mid-shift Issue Records")
        midshift_issues = get_midshift_issues()
        
        if st.session_state.role == "admin":
            if midshift_issues:
                data = []
                for issue in midshift_issues:
                    _, agent, issue_type, start_time, end_time, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Issue Type": issue_type,
                        "Start time": start_time,
                        "End Time": end_time
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="midshift_issues.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_midshift_issues()
                    st.rerun()
            else:
                st.info("No mid-shift issue records found")
        else:
            user_issues = [issue for issue in midshift_issues if issue[1] == st.session_state.username]
            if user_issues:
                data = []
                for issue in user_issues:
                    _, agent, issue_type, start_time, end_time, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Issue Type": issue_type,
                        "Start time": start_time,
                        "End Time": end_time
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no mid-shift issue records")

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

        with st.expander("❌ Clear All Late Logins"):
            with st.form("clear_late_logins_form"):
                st.warning("This will permanently delete ALL late login records!")
                if st.form_submit_button("Clear All Late Logins"):
                    if clear_late_logins():
                        st.success("All late login records deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Quality Issues"):
            with st.form("clear_quality_issues_form"):
                st.warning("This will permanently delete ALL quality issue records!")
                if st.form_submit_button("Clear All Quality Issues"):
                    if clear_quality_issues():
                        st.success("All quality issue records deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Mid-shift Issues"):
            with st.form("clear_midshift_issues_form"):
                st.warning("This will permanently delete ALL mid-shift issue records!")
                if st.form_submit_button("Clear All Mid-shift Issues"):
                    if clear_midshift_issues():
                        st.success("All mid-shift issue records deleted!")
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
                        clear_late_logins()
                        clear_quality_issues()
                        clear_midshift_issues()
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
