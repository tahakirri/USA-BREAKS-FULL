import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, time
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
        
        # Add break template table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                max_users_per_slot INTEGER,
                is_active INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TEXT)
        """)
        
        # Add break slots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                break_type TEXT CHECK(break_type IN ('first_tea', 'lunch', 'second_tea')),
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY(template_id) REFERENCES break_templates(id))
        """)
        
        # Add break bookings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS break_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                template_id INTEGER,
                slot_id INTEGER,
                booking_date TEXT,
                created_at TEXT,
                FOREIGN KEY(template_id) REFERENCES break_templates(id),
                FOREIGN KEY(slot_id) REFERENCES break_slots(id))
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
# Fancy Number Checker Functions
# --------------------------

def is_sequential(digits, step=1):
    """Check if digits form a sequential pattern with given step"""
    try:
        return all(int(digits[i]) == int(digits[i-1]) + step for i in range(1, len(digits)))
    except:
        return False

def is_fancy_number(phone_number):
    clean_number = re.sub(r'\D', '', phone_number)
    
    # Get last 6 digits according to Lycamobile policy
    if len(clean_number) >= 6:
        last_six = clean_number[-6:]
        last_three = clean_number[-3:]
    else:
        return False, "Number too short (need at least 6 digits)"
    
    patterns = []
    
    # Special case for 13322866688
    if clean_number == "13322866688":
        patterns.append("Special VIP number (13322866688)")
    
    # Check for ABBBAA pattern (like 566655)
    if (len(last_six) == 6 and 
        last_six[0] == last_six[5] and 
        last_six[1] == last_six[2] == last_six[3] and 
        last_six[4] == last_six[0] and 
        last_six[0] != last_six[1]):
        patterns.append("ABBBAA pattern (e.g., 566655)")
    
    # Check for ABBBA pattern (like 233322)
    if (len(last_six) >= 5 and 
        last_six[0] == last_six[4] and 
        last_six[1] == last_six[2] == last_six[3] and 
        last_six[0] != last_six[1]):
        patterns.append("ABBBA pattern (e.g., 233322)")
    
    # 1. 6-digit patterns (strict matches only)
    # All same digits (666666)
    if len(set(last_six)) == 1:
        patterns.append("6 identical digits")
    
    # Consecutive ascending (123456)
    if is_sequential(last_six, 1):
        patterns.append("6-digit ascending sequence")
        
    # Consecutive descending (654321)
    if is_sequential(last_six, -1):
        patterns.append("6-digit descending sequence")
        
    # Palindrome (100001)
    if last_six == last_six[::-1]:
        patterns.append("6-digit palindrome")
    
    # 2. 3-digit patterns (strict matches from image)
    first_triple = last_six[:3]
    second_triple = last_six[3:]
    
    # Double triplets (444555)
    if len(set(first_triple)) == 1 and len(set(second_triple)) == 1 and first_triple != second_triple:
        patterns.append("Double triplets (444555)")
    
    # Similar triplets (121122)
    if (first_triple[0] == first_triple[1] and 
        second_triple[0] == second_triple[1] and 
        first_triple[2] == second_triple[2]):
        patterns.append("Similar triplets (121122)")
    
    # Repeating triplets (786786)
    if first_triple == second_triple:
        patterns.append("Repeating triplets (786786)")
    
    # Nearly sequential (457456) - exactly 1 digit difference
    if abs(int(first_triple) - int(second_triple)) == 1:
        patterns.append("Nearly sequential triplets (457456)")
    
    # 3. 2-digit patterns (strict matches from image)
    # Incremental pairs (111213)
    pairs = [last_six[i:i+2] for i in range(0, 5, 1)]
    try:
        if all(int(pairs[i]) == int(pairs[i-1]) + 1 for i in range(1, len(pairs))):
            patterns.append("Incremental pairs (111213)")
    
        # Repeating pairs (202020)
        if (pairs[0] == pairs[2] == pairs[4] and 
            pairs[1] == pairs[3] and 
            pairs[0] != pairs[1]):
            patterns.append("Repeating pairs (202020)")
    
        # Alternating pairs (010101)
        if (pairs[0] == pairs[2] == pairs[4] and 
            pairs[1] == pairs[3] and 
            pairs[0] != pairs[1]):
            patterns.append("Alternating pairs (010101)")
    
        # Stepping pairs (324252) - Fixed this check
        if (all(int(pairs[i][0]) == int(pairs[i-1][0]) + 1 for i in range(1, len(pairs))) and
            all(int(pairs[i][1]) == int(pairs[i-1][1]) + 2 for i in range(1, len(pairs)))):
            patterns.append("Stepping pairs (324252)")
    except:
        pass
    
    # 4. Exceptional cases (must match exactly)
    exceptional_triplets = ['123', '555', '777', '999']
    if last_three in exceptional_triplets:
        patterns.append(f"Exceptional case ({last_three})")
    
    # Strict validation - only allow patterns that exactly match our rules
    valid_patterns = []
    for p in patterns:
        if any(rule in p for rule in [
            "Special VIP number",
            "ABBBAA pattern",
            "ABBBA pattern",
            "6 identical digits",
            "6-digit ascending sequence",
            "6-digit descending sequence",
            "6-digit palindrome",
            "Double triplets (444555)",
            "Similar triplets (121122)",
            "Repeating triplets (786786)",
            "Nearly sequential triplets (457456)",
            "Incremental pairs (111213)",
            "Repeating pairs (202020)",
            "Alternating pairs (010101)",
            "Stepping pairs (324252)",
            "Exceptional case"
        ]):
            valid_patterns.append(p)
    
    return bool(valid_patterns), ", ".join(valid_patterns) if valid_patterns else "No qualifying fancy pattern"

# --------------------------
# Streamlit App
# --------------------------

st.set_page_config(
    page_title="Request Management System",
    page_icon=":office:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
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
    .editable-break {
        background-color: #2D3748;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .stTimeInput > div > div > input {
        padding: 0.5rem;
    }
    .time-input {
        font-family: monospace;
    }
    /* Fancy number checker styles */
    .fancy-number { color: #00ff00; font-weight: bold; }
    .normal-number { color: #ffffff; }
    .result-box { padding: 15px; border-radius: 5px; margin: 10px 0; }
    .fancy-result { background-color: #1e3d1e; border: 1px solid #00ff00; }
    .normal-result { background-color: #3d1e1e; border: 1px solid #ff0000; }
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
            ("⏸️ Break Booking", "break_booking"),
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
            nav_options.append(("⚙️ Break Admin", "break_admin"))
        
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
        st.header("📱 Lycamobile Fancy Number Checker")
        st.subheader("Official Policy: Analyzes last 6 digits only for qualifying patterns")

        phone_input = st.text_input("Enter Phone Number", 
                                  placeholder="e.g., 1555123456 or 44207123456")

        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("🔍 Check Number"):
                if not phone_input:
                    st.warning("Please enter a phone number")
                else:
                    is_fancy, pattern = is_fancy_number(phone_input)
                    clean_number = re.sub(r'\D', '', phone_input)
                    
                    # Extract last 6 digits for display
                    last_six = clean_number[-6:] if len(clean_number) >= 6 else clean_number
                    formatted_num = f"{last_six[:3]}-{last_six[3:]}" if len(last_six) == 6 else last_six

                    if is_fancy:
                        st.markdown(f"""
                        <div class="result-box fancy-result">
                            <h3><span class="fancy-number">✨ {formatted_num} ✨</span></h3>
                            <p>FANCY NUMBER DETECTED!</p>
                            <p><strong>Pattern:</strong> {pattern}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="result-box normal-result">
                            <h3><span class="normal-number">{formatted_num}</span></h3>
                            <p>Standard phone number</p>
                            <p><strong>Reason:</strong> {pattern}</p>
                        </div>
                        """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            ### Lycamobile Fancy Number Policy
            **Qualifying Patterns (last 6 digits only):**
            
            #### 6-Digit Patterns
            - 123456 (ascending)
            - 987654 (descending)
            - 666666 (repeating)
            - 100001 (palindrome)
            
            #### 3-Digit Patterns  
            - 444 555 (double triplets)
            - 121 122 (similar triplets)
            - 786 786 (repeating triplets)
            - 457 456 (nearly sequential)
            
            #### 2-Digit Patterns
            - 11 12 13 (incremental)
            - 20 20 20 (repeating)
            - 01 01 01 (alternating)
            - 32 42 52 (stepping)
            
            #### Exceptional Cases
            - Ending with 123/555/777/999
            """)

        # Test cases
        debug_mode = st.checkbox("Show test cases", False)
        if debug_mode:
            test_numbers = [
                ("16109055580", False),  # 055580 → No pattern ✗
                ("123456", True),       # 6-digit ascending ✓
                ("444555", True),       # Double triplets ✓
                ("121122", True),       # Similar triplets ✓ 
                ("111213", True),       # Incremental pairs ✓
                ("202020", True),       # Repeating pairs ✓
                ("010101", True),       # Alternating pairs ✓
                ("324252", True),       # Stepping pairs ✓
                ("7900000123", True),   # Ends with 123 ✓
                ("123458", False),      # No pattern ✗
                ("112233", False),      # Not in our strict rules ✗
                ("555555", True)        # 6 identical digits ✓
            ]
            
            st.markdown("### Strict Policy Validation")
            for number, expected in test_numbers:
                is_fancy, pattern = is_fancy_number(number)
                result = "PASS" if is_fancy == expected else "FAIL"
                color = "green" if result == "PASS" else "red"
                st.write(f"<span style='color:{color}'>{number[-6:]}: {result} ({pattern})</span>", unsafe_allow_html=True)

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
                    # Validate time formats
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
                # Prepare data for download
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
                
                # Download button
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
            # For agents, only show their own records
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
                # Prepare data for download
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
                
                # Download button
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
            # For agents, only show their own records
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
                # Prepare data for download
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
                
                # Download button
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
            # For agents, only show their own records
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

    elif st.session_state.current_section == "break_booking":
        # Initialize break booking system files if they don't exist
        BOOKINGS_FILE = "data/break_bookings.json"
        SETTINGS_FILE = "data/break_settings.json"
        TEMPLATES_FILE = "data/break_templates.json"
        
        os.makedirs("data", exist_ok=True)
        
        # Initialize default settings if not exists
        if not os.path.exists(SETTINGS_FILE):
            default_settings = {
                "max_per_slot": 3,
                "current_template": "default",
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_settings, f)
        
        # Initialize default templates if not exists
        if not os.path.exists(TEMPLATES_FILE):
            default_templates = {
                "2pm_english": {
                    "description": "2 PM English Team Break Schedule",
                    "flag": "🇺🇸",
                    "language": "English",
                    "shift": "2pm",
                    "early_tea": {"start": "15:00", "end": "16:30", "slots": ["15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"]},
                    "lunch": {"start": "18:30", "end": "20:30", "slots": ["18:30", "19:00", "19:30", "20:00", "20:30"]},
                    "late_tea": {"start": "20:45", "end": "21:30", "slots": ["20:45", "21:00", "21:15", "21:30"]}
                },
                "6pm_english": {
                    "description": "6 PM English Team Break Schedule",
                    "flag": "🇺🇸",
                    "language": "English",
                    "shift": "6pm",
                    "early_tea": {"start": "19:00", "end": "20:45", "slots": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"]},
                    "lunch": {"start": "21:00", "end": "22:30", "slots": ["21:00", "21:30", "22:00", "22:30"]},
                    "late_tea": {"start": "00:00", "end": "01:30", "slots": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]}
                },
                "2pm_spanish": {
                    "description": "2 PM Spanish Team Break Schedule",
                    "flag": "🇪🇸",
                    "language": "Spanish",
                    "shift": "2pm",
                    "early_tea": {"start": "15:00", "end": "16:30", "slots": ["15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"]},
                    "lunch": {"start": "18:30", "end": "20:30", "slots": ["18:30", "19:00", "19:30", "20:00", "20:30"]},
                    "late_tea": {"start": "20:45", "end": "21:30", "slots": ["20:45", "21:00", "21:15", "21:30"]}
                },
                "6pm_spanish": {
                    "description": "6 PM Spanish Team Break Schedule",
                    "flag": "🇪🇸",
                    "language": "Spanish",
                    "shift": "6pm",
                    "early_tea": {"start": "19:00", "end": "20:45", "slots": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"]},
                    "lunch": {"start": "21:00", "end": "22:30", "slots": ["21:00", "21:30", "22:00", "22:30"]},
                    "late_tea": {"start": "00:00", "end": "01:30", "slots": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]}
                }
            }
            with open(TEMPLATES_FILE, "w") as f:
                json.dump(default_templates, f)
        
        # Initialize empty bookings file if not exists
        if not os.path.exists(BOOKINGS_FILE):
            with open(BOOKINGS_FILE, "w") as f:
                json.dump({}, f)
        
        # Load settings and templates
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        with open(TEMPLATES_FILE, "r") as f:
            templates = json.load(f)
        with open(BOOKINGS_FILE, "r") as f:
            bookings = json.load(f)
        
        st.title("⏸️ Break Booking")
        
        # Date selection
        selected_date = st.date_input("Select Date", 
                                    min_value=datetime.now().date(),
                                    value=datetime.now().date())
        date_str = selected_date.strftime("%Y-%m-%d")
        
        # Create tabs for the two shifts
        tab1, tab2 = st.tabs(["2:00 PM Shift", "6:00 PM Shift"])
        
        current_template = templates[settings["current_template"]]
        max_per_slot = settings["max_per_slot"]
        
        def get_slot_bookings(shift, break_type, slot):
            try:
                return len(bookings[date_str][shift][break_type][slot])
            except KeyError:
                return 0
        
        def get_agent_bookings():
            agent_bookings = {"2pm": {}, "6pm": {}}
            if date_str in bookings:
                for shift in bookings[date_str]:
                    for break_type in bookings[date_str][shift]:
                        for slot in bookings[date_str][shift][break_type]:
                            if st.session_state.username in bookings[date_str][shift][break_type][slot]:
                                if break_type not in agent_bookings[shift]:
                                    agent_bookings[shift][break_type] = []
                                agent_bookings[shift][break_type].append(slot)
            return agent_bookings
        
        def add_booking(shift, break_type, slot):
            if date_str not in bookings:
                bookings[date_str] = {}
            if shift not in bookings[date_str]:
                bookings[date_str][shift] = {}
            if break_type not in bookings[date_str][shift]:
                bookings[date_str][shift][break_type] = {}
            if slot not in bookings[date_str][shift][break_type]:
                bookings[date_str][shift][break_type][slot] = []
            
            if st.session_state.username not in bookings[date_str][shift][break_type][slot]:
                bookings[date_str][shift][break_type][slot].append(st.session_state.username)
                with open(BOOKINGS_FILE, "w") as f:
                    json.dump(bookings, f)
                return True
            return False
        
        def remove_booking(shift, break_type, slot):
            if (date_str in bookings and shift in bookings[date_str] and 
                break_type in bookings[date_str][shift] and 
                slot in bookings[date_str][shift][break_type] and 
                st.session_state.username in bookings[date_str][shift][break_type][slot]):
                
                bookings[date_str][shift][break_type][slot].remove(st.session_state.username)
                
                # Clean up empty structures
                if not bookings[date_str][shift][break_type][slot]:
                    del bookings[date_str][shift][break_type][slot]
                if not bookings[date_str][shift][break_type]:
                    del bookings[date_str][shift][break_type]
                if not bookings[date_str][shift]:
                    del bookings[date_str][shift]
                if not bookings[date_str]:
                    del bookings[date_str]
                
                with open(BOOKINGS_FILE, "w") as f:
                    json.dump(bookings, f)
                return True
            return False
        
        agent_bookings = get_agent_bookings()
        
        # 2 PM Shift
        with tab1:
            st.subheader("2:00 PM Shift")
            col1, col2, col3 = st.columns(3)
            
            # Early Tea Break
            with col1:
                st.markdown("### Early Tea Break")
                early_tea_booked = "early_tea" in agent_bookings["2pm"]
                
                if early_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['early_tea'])}")
                    if st.button("Cancel Early Tea Booking (2PM)"):
                        for slot in agent_bookings["2pm"]["early_tea"]:
                            remove_booking("2pm", "early_tea", slot)
                        st.rerun()
                else:
                    early_tea_options = []
                    for slot in current_template["shifts"]["2pm"]["early_tea"]["slots"]:
                        count = get_slot_bookings("2pm", "early_tea", slot)
                        if count < max_per_slot:
                            early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if early_tea_options:
                        selected_early_tea = st.selectbox("Select Early Tea Time (2PM)", early_tea_options)
                        if st.button("Book Early Tea Break (2PM)"):
                            slot = selected_early_tea.split(" ")[0]
                            if add_booking("2pm", "early_tea", slot):
                                st.success(f"Booked Early Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Early Tea Break")
            
            # Lunch Break
            with col2:
                st.markdown("### Lunch Break")
                lunch_booked = "lunch" in agent_bookings["2pm"]
                
                if lunch_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['lunch'])}")
                    if st.button("Cancel Lunch Booking (2PM)"):
                        for slot in agent_bookings["2pm"]["lunch"]:
                            remove_booking("2pm", "lunch", slot)
                        st.rerun()
                else:
                    lunch_options = []
                    for slot in current_template["shifts"]["2pm"]["lunch"]["slots"]:
                        count = get_slot_bookings("2pm", "lunch", slot)
                        if count < max_per_slot:
                            lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if lunch_options:
                        selected_lunch = st.selectbox("Select Lunch Time (2PM)", lunch_options)
                        if st.button("Book Lunch Break (2PM)"):
                            slot = selected_lunch.split(" ")[0]
                            if add_booking("2pm", "lunch", slot):
                                st.success(f"Booked Lunch Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Lunch Break")
            
            # Late Tea Break
            with col3:
                st.markdown("### Late Tea Break")
                late_tea_booked = "late_tea" in agent_bookings["2pm"]
                
                if late_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['late_tea'])}")
                    if st.button("Cancel Late Tea Booking (2PM)"):
                        for slot in agent_bookings["2pm"]["late_tea"]:
                            remove_booking("2pm", "late_tea", slot)
                        st.rerun()
                else:
                    late_tea_options = []
                    for slot in current_template["shifts"]["2pm"]["late_tea"]["slots"]:
                        count = get_slot_bookings("2pm", "late_tea", slot)
                        if count < max_per_slot:
                            late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if late_tea_options:
                        selected_late_tea = st.selectbox("Select Late Tea Time (2PM)", late_tea_options)
                        if st.button("Book Late Tea Break (2PM)"):
                            slot = selected_late_tea.split(" ")[0]
                            if add_booking("2pm", "late_tea", slot):
                                st.success(f"Booked Late Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Late Tea Break")
        
        # 6 PM Shift
        with tab2:
            st.subheader("6:00 PM Shift")
            col1, col2, col3 = st.columns(3)
            
            # Early Tea Break
            with col1:
                st.markdown("### Early Tea Break")
                early_tea_booked = "early_tea" in agent_bookings["6pm"]
                
                if early_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['early_tea'])}")
                    if st.button("Cancel Early Tea Booking (6PM)"):
                        for slot in agent_bookings["6pm"]["early_tea"]:
                            remove_booking("6pm", "early_tea", slot)
                        st.rerun()
                else:
                    early_tea_options = []
                    for slot in current_template["shifts"]["6pm"]["early_tea"]["slots"]:
                        count = get_slot_bookings("6pm", "early_tea", slot)
                        if count < max_per_slot:
                            early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if early_tea_options:
                        selected_early_tea = st.selectbox("Select Early Tea Time (6PM)", early_tea_options)
                        if st.button("Book Early Tea Break (6PM)"):
                            slot = selected_early_tea.split(" ")[0]
                            if add_booking("6pm", "early_tea", slot):
                                st.success(f"Booked Early Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Early Tea Break")
            
            # Lunch Break
            with col2:
                st.markdown("### Lunch Break")
                lunch_booked = "lunch" in agent_bookings["6pm"]
                
                if lunch_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['lunch'])}")
                    if st.button("Cancel Lunch Booking (6PM)"):
                        for slot in agent_bookings["6pm"]["lunch"]:
                            remove_booking("6pm", "lunch", slot)
                        st.rerun()
                else:
                    lunch_options = []
                    for slot in current_template["shifts"]["6pm"]["lunch"]["slots"]:
                        count = get_slot_bookings("6pm", "lunch", slot)
                        if count < max_per_slot:
                            lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if lunch_options:
                        selected_lunch = st.selectbox("Select Lunch Time (6PM)", lunch_options)
                        if st.button("Book Lunch Break (6PM)"):
                            slot = selected_lunch.split(" ")[0]
                            if add_booking("6pm", "lunch", slot):
                                st.success(f"Booked Lunch Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Lunch Break")
            
            # Late Tea Break
            with col3:
                st.markdown("### Late Tea Break")
                late_tea_booked = "late_tea" in agent_bookings["6pm"]
                
                if late_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['late_tea'])}")
                    if st.button("Cancel Late Tea Booking (6PM)"):
                        for slot in agent_bookings["6pm"]["late_tea"]:
                            remove_booking("6pm", "late_tea", slot)
                        st.rerun()
                else:
                    late_tea_options = []
                    for slot in current_template["shifts"]["6pm"]["late_tea"]["slots"]:
                        count = get_slot_bookings("6pm", "late_tea", slot)
                        if count < max_per_slot:
                            late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if late_tea_options:
                        selected_late_tea = st.selectbox("Select Late Tea Time (6PM)", late_tea_options)
                        if st.button("Book Late Tea Break (6PM)"):
                            slot = selected_late_tea.split(" ")[0]
                            if add_booking("6pm", "late_tea", slot):
                                st.success(f"Booked Late Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Late Tea Break")

    elif st.session_state.current_section == "break_admin":
        if st.session_state.role == "admin":
            st.title("⚙️ Break Booking Administration")
            
            # Load break booking data
            BOOKINGS_FILE = "data/break_bookings.json"
            SETTINGS_FILE = "data/break_settings.json"
            TEMPLATES_FILE = "data/break_templates.json"
            
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
            with open(TEMPLATES_FILE, "r") as f:
                templates = json.load(f)
            with open(BOOKINGS_FILE, "r") as f:
                bookings = json.load(f)
            
            # Create tabs for different admin functions
            tab1, tab2, tab3, tab4 = st.tabs(["View Bookings", "Manage Slots", "Settings", "Templates"])
            
            # Tab 1: View Bookings
            with tab1:
                st.subheader("View All Bookings")
                
                # Date selector
                selected_date = st.date_input("Select Date to View")
                date_str = selected_date.strftime("%Y-%m-%d")
                
                # Get current template
                current_template = templates[settings["current_template"]]
                
                if date_str in bookings:
                    # 2 PM Shift
                    st.markdown("### 2:00 PM Shift")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("#### Early Tea Break")
                        if "2pm" in bookings[date_str] and "early_tea" in bookings[date_str]["2pm"]:
                            data = []
                            for slot in current_template["early_tea"]["slots"]:
                                if slot in bookings[date_str]["2pm"]["early_tea"]:
                                    for agent in bookings[date_str]["2pm"]["early_tea"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                    
                    with col2:
                        st.markdown("#### Lunch Break")
                        if "2pm" in bookings[date_str] and "lunch" in bookings[date_str]["2pm"]:
                            data = []
                            for slot in current_template["lunch"]["slots"]:
                                if slot in bookings[date_str]["2pm"]["lunch"]:
                                    for agent in bookings[date_str]["2pm"]["lunch"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                    
                    with col3:
                        st.markdown("#### Late Tea Break")
                        if "2pm" in bookings[date_str] and "late_tea" in bookings[date_str]["2pm"]:
                            data = []
                            for slot in current_template["late_tea"]["slots"]:
                                if slot in bookings[date_str]["2pm"]["late_tea"]:
                                    for agent in bookings[date_str]["2pm"]["late_tea"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                    
                    # 6 PM Shift
                    st.markdown("### 6:00 PM Shift")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("#### Early Tea Break")
                        if "6pm" in bookings[date_str] and "early_tea" in bookings[date_str]["6pm"]:
                            data = []
                            for slot in current_template["early_tea"]["slots"]:
                                if slot in bookings[date_str]["6pm"]["early_tea"]:
                                    for agent in bookings[date_str]["6pm"]["early_tea"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                    
                    with col2:
                        st.markdown("#### Lunch Break")
                        if "6pm" in bookings[date_str] and "lunch" in bookings[date_str]["6pm"]:
                            data = []
                            for slot in current_template["lunch"]["slots"]:
                                if slot in bookings[date_str]["6pm"]["lunch"]:
                                    for agent in bookings[date_str]["6pm"]["lunch"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                    
                    with col3:
                        st.markdown("#### Late Tea Break")
                        if "6pm" in bookings[date_str] and "late_tea" in bookings[date_str]["6pm"]:
                            data = []
                            for slot in current_template["late_tea"]["slots"]:
                                if slot in bookings[date_str]["6pm"]["late_tea"]:
                                    for agent in bookings[date_str]["6pm"]["late_tea"][slot]:
                                        data.append({"Time": slot, "Agent": agent})
                            if data:
                                st.dataframe(pd.DataFrame(data))
                            else:
                                st.info("No bookings")
                        else:
                            st.info("No bookings")
                else:
                    st.info(f"No bookings found for {date_str}")
            
            # Tab 2: Manage Slots
            with tab2:
                st.subheader("Manage Break Slots")
                
                shift_option = st.selectbox("Select Shift", ["2pm", "6pm"])
                break_type_option = st.selectbox("Select Break Type", ["early_tea", "lunch", "late_tea"])
                
                current_template = templates[settings["current_template"]]
                current_slots = current_template["shifts"][shift_option][break_type_option]["slots"]
                
                st.write("Current Slots:")
                st.write(", ".join(current_slots))
                
                new_slots = st.text_area("Edit Slots (comma-separated times in 24-hour format)", 
                                       value=", ".join(current_slots))
                
                if st.button("Update Slots"):
                    try:
                        slots_list = [slot.strip() for slot in new_slots.split(",")]
                        
                        # Validate time format
                        for slot in slots_list:
                            parts = slot.split(":")
                            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                                raise ValueError(f"Invalid time format: {slot}")
                            
                            hours = int(parts[0])
                            minutes = int(parts[1])
                            
                            if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                                raise ValueError(f"Invalid time: {slot}")
                        
                        # Update template
                        current_template_name = settings["current_template"]
                        templates[current_template_name]["shifts"][shift_option][break_type_option]["slots"] = slots_list
                        with open(TEMPLATES_FILE, "w") as f:
                            json.dump(templates, f)
                        st.success("Slots updated successfully!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {str(e)}")
            
            # Tab 3: Settings
            with tab3:
                st.subheader("System Settings")
                
                max_per_slot = st.number_input("Maximum Bookings Per Slot", 
                                             min_value=1, 
                                             max_value=20, 
                                             value=settings["max_per_slot"])
                
                if st.button("Update Max Bookings"):
                    settings["max_per_slot"] = int(max_per_slot)
                    with open(SETTINGS_FILE, "w") as f:
                        json.dump(settings, f)
                    st.success(f"Maximum bookings per slot updated to {max_per_slot}!")
                    st.rerun()
                
                st.markdown("### Delete All Bookings for a Date")
                delete_date = st.date_input("Select Date to Delete")
                delete_date_str = delete_date.strftime("%Y-%m-%d")
                
                if st.button("Delete All Bookings"):
                    if delete_date_str in bookings:
                        del bookings[delete_date_str]
                        with open(BOOKINGS_FILE, "w") as f:
                            json.dump(bookings, f)
                        st.success(f"All bookings for {delete_date_str} have been deleted!")
                        st.rerun()
                    else:
                        st.info(f"No bookings found for {delete_date_str}")
            
            # Tab 4: Templates
            with tab4:
                st.subheader("Manage Break Templates")
                
                current_template_name = settings["current_template"]
                st.markdown(f"**Current Template:** {current_template_name}")
                st.markdown(f"**Description:** {templates[current_template_name].get('description', 'No description')}")
                
                template_names = list(templates.keys())
                selected_template = st.selectbox("Select Template", template_names, 
                                              index=template_names.index(current_template_name))
                
                if st.button("Set as Active Template"):
                    settings["current_template"] = selected_template
                    with open(SETTINGS_FILE, "w") as f:
                        json.dump(settings, f)
                    st.success(f"Template '{selected_template}' is now active!")
                    st.rerun()
                
                st.markdown("### Create New Template")
                new_template_name = st.text_input("New Template Name")
                new_template_description = st.text_input("Description")
                copy_from = st.selectbox("Copy settings from", template_names)
                
                if st.button("Create New Template"):
                    if new_template_name in templates:
                        st.error("A template with this name already exists!")
                    elif not new_template_name:
                        st.error("Please enter a template name")
                    else:
                        new_template = {
                            "description": new_template_description,
                            "shifts": json.loads(json.dumps(templates[copy_from]["shifts"]))
                        }
                        templates[new_template_name] = new_template
                        with open(TEMPLATES_FILE, "w") as f:
                            json.dump(templates, f)
                        st.success(f"Template '{new_template_name}' created!")
                        st.rerun()
                
                if len(templates) > 1:
                    st.markdown("### Delete Template")
                    template_to_delete = st.selectbox("Select template to delete", 
                                                    [t for t in template_names if t != "default"])
                    
                    if st.button("Delete Template"):
                        if template_to_delete == settings["current_template"]:
                            st.error("Cannot delete the active template. Please select another template first.")
                        else:
                            del templates[template_to_delete]
                            with open(TEMPLATES_FILE, "w") as f:
                                json.dump(templates, f)
                            st.success(f"Template '{template_to_delete}' deleted!")
                            st.rerun()
        else:
            st.error("Access Denied: You don't have permission to view this section.")
            if st.session_state.current_section == "break_admin":
                st.session_state.current_section = "requests"
                st.rerun()

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

# --------------------------
# Break Template Functions
# --------------------------

def create_break_template(name, max_users_per_slot, created_by):
    try:
        if is_killswitch_enabled():
            st.error("System is currently locked. Please contact the developer.")
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if template with same name exists
        cursor.execute("SELECT id FROM break_templates WHERE name = ?", (name,))
        if cursor.fetchone():
            st.error("A template with this name already exists")
            return None
            
        # Insert new template
        cursor.execute("""
            INSERT INTO break_templates (name, max_users_per_slot, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (name, max_users_per_slot, created_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        template_id = cursor.lastrowid
        conn.commit()
        return template_id
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def add_break_slot(template_id, break_type, start_time, end_time):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO break_slots (template_id, break_type, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (template_id, break_type, start_time, end_time))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_break_templates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM break_templates WHERE is_active = 1")
        return cursor.fetchall()
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_break_slots(template_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM break_slots WHERE template_id = ?", (template_id,))
        return cursor.fetchall()
    finally:
        conn.close()

def get_slot_bookings(slot_id, date):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM break_bookings 
            WHERE slot_id = ? AND booking_date = ?
        """, (slot_id, date))
        return cursor.fetchone()[0]
    finally:
        conn.close()

def book_break(agent_name, template_id, slot_id, date):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Check if agent already has a booking for this break type on this date
        cursor.execute("""
            SELECT bs.break_type 
            FROM break_bookings bb 
            JOIN break_slots bs ON bb.slot_id = bs.id 
            WHERE bb.agent_name = ? AND bb.booking_date = ?
        """, (agent_name, date))
        existing_bookings = cursor.fetchall()
        existing_break_types = [b[0] for b in existing_bookings]
        
        # Get break type for requested slot
        cursor.execute("SELECT break_type FROM break_slots WHERE id = ?", (slot_id,))
        requested_break_type = cursor.fetchone()[0]
        
        if requested_break_type in existing_break_types:
            st.error(f"You already have a booking for this break type on {date}")
            return False
        
        # Check if slot is full
        current_bookings = get_slot_bookings(slot_id, date)
        cursor.execute("SELECT max_users_per_slot FROM break_templates WHERE id = ?", (template_id,))
        max_users = cursor.fetchone()[0]
        
        if current_bookings >= max_users:
            st.error("This slot is full")
            return False
        
        cursor.execute("""
            INSERT INTO break_bookings (agent_name, template_id, slot_id, booking_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, template_id, slot_id, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_agent_bookings(agent_name, date=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if date:
            cursor.execute("""
                SELECT bb.*, bt.name, bs.break_type, bs.start_time, bs.end_time
                FROM break_bookings bb
                JOIN break_templates bt ON bb.template_id = bt.id
                JOIN break_slots bs ON bb.slot_id = bs.id
                WHERE bb.agent_name = ? AND bb.booking_date = ?
                ORDER BY bs.start_time
            """, (agent_name, date))
        else:
            cursor.execute("""
                SELECT bb.*, bt.name, bs.break_type, bs.start_time, bs.end_time
                FROM break_bookings bb
                JOIN break_templates bt ON bb.template_id = bt.id
                JOIN break_slots bs ON bb.slot_id = bs.id
                WHERE bb.agent_name = ?
                ORDER BY bb.booking_date, bs.start_time
            """, (agent_name,))
        return cursor.fetchall()
    finally:
        conn.close()

def cancel_booking(booking_id):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM break_bookings WHERE id = ?", (booking_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def toggle_template(template_id, active):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE break_templates SET is_active = ? WHERE id = ?", 
                      (1 if active else 0, template_id))
        conn.commit()
        return True
    finally:
        conn.close()

def break_booking_interface():
    st.title("⏸️ Break Booking")
    
    # Date selection
    selected_date = st.date_input("Select Date", 
                                 min_value=datetime.now().date(),
                                 value=datetime.now().date())
    
    # Get available templates
    templates = get_break_templates()
    if not templates:
        st.info("No break templates available. Please contact your administrator.")
        return
    
    # Show booking form
    with st.form("break_booking_form"):
        template_id = st.selectbox("Select Template", 
                                 options=[t[0] for t in templates],
                                 format_func=lambda x: next(t[1] for t in templates if t[0] == x))
        
        # Get slots for selected template
        slots = get_break_slots(template_id)
        slot_options = []
        for slot in slots:
            slot_id, _, break_type, start_time, end_time = slot
            bookings = get_slot_bookings(slot_id, selected_date.strftime("%Y-%m-%d"))
            max_users = next(t[2] for t in templates if t[0] == template_id)
            break_name = {
                "first_tea": "First Tea Break",
                "lunch": "Lunch Break",
                "second_tea": "Second Tea Break"
            }[break_type]
            slot_options.append((slot_id, 
                               f"{break_name} ({start_time}-{end_time}) - {bookings}/{max_users} booked"))
        
        selected_slot = st.selectbox("Select Break Slot", 
                                   options=[s[0] for s in slot_options],
                                   format_func=lambda x: next(s[1] for s in slot_options if s[0] == x))
        
        if st.form_submit_button("Book Break"):
            if book_break(st.session_state.username, template_id, selected_slot, 
                         selected_date.strftime("%Y-%m-%d")):
                st.success("Break booked successfully!")
                st.rerun()
    
    # Show user's bookings
    st.subheader("Your Bookings")
    bookings = get_agent_bookings(st.session_state.username)
    if bookings:
        for booking in bookings:
            booking_id, _, _, _, booking_date, _, template_name, break_type, start_time, end_time = booking
            break_name = {
                "first_tea": "First Tea Break",
                "lunch": "Lunch Break",
                "second_tea": "Second Tea Break"
            }[break_type]
            
            cols = st.columns([3, 1])
            cols[0].write(f"""
            **{break_name}** ({start_time}-{end_time})  
            Template: {template_name}  
            Date: {booking_date}
            """)
            
            if cols[1].button("Cancel", key=f"cancel_{booking_id}"):
                if cancel_booking(booking_id):
                    st.success("Booking cancelled!")
                    st.rerun()
    else:
        st.info("You have no break bookings")

def break_booking_admin_interface():
    st.title("⚙️ Break Booking Administration")
    
    # Create new template
    with st.expander("Create New Template"):
        with st.form("create_template"):
            template_name = st.text_input("Template Name")
            max_users = st.number_input("Maximum Users per Slot", min_value=1, value=5)
            
            # First Tea Break
            st.subheader("First Tea Break")
            first_tea_start = st.text_input("Start Time (HH:MM)", value="10:00", key="first_tea_start")
            first_tea_end = st.text_input("End Time (HH:MM)", value="10:15", key="first_tea_end")
            
            # Lunch Break
            st.subheader("Lunch Break")
            lunch_start = st.text_input("Start Time (HH:MM)", value="13:00", key="lunch_start")
            lunch_end = st.text_input("End Time (HH:MM)", value="14:00", key="lunch_end")
            
            # Second Tea Break
            st.subheader("Second Tea Break")
            second_tea_start = st.text_input("Start Time (HH:MM)", value="15:30", key="second_tea_start")
            second_tea_end = st.text_input("End Time (HH:MM)", value="15:45", key="second_tea_end")
            
            if st.form_submit_button("Create Template"):
                try:
                    # Validate time formats
                    times = [first_tea_start, first_tea_end, lunch_start, lunch_end, 
                            second_tea_start, second_tea_end]
                    for t in times:
                        datetime.strptime(t, "%H:%M")
                    
                    # Create template
                    template_id = create_break_template(template_name, max_users, st.session_state.username)
                    if template_id:
                        # Add slots
                        add_break_slot(template_id, "first_tea", first_tea_start, first_tea_end)
                        add_break_slot(template_id, "lunch", lunch_start, lunch_end)
                        add_break_slot(template_id, "second_tea", second_tea_start, second_tea_end)
                        st.success("Template created successfully!")
                        st.rerun()
                except ValueError:
                    st.error("Invalid time format. Please use HH:MM format (e.g., 09:30)")
    
    # Manage existing templates
    st.subheader("Manage Templates")
    templates = get_break_templates()
    for template in templates:
        template_id, name, max_users, is_active, created_by, created_at = template
        
        with st.expander(f"Template: {name}"):
            st.write(f"Created by: {created_by}")
            st.write(f"Created at: {created_at}")
            st.write(f"Max users per slot: {max_users}")
            
            # Show slots
            slots = get_break_slots(template_id)
            for slot in slots:
                slot_id, _, break_type, start_time, end_time = slot
                break_name = {
                    "first_tea": "First Tea Break",
                    "lunch": "Lunch Break",
                    "second_tea": "Second Tea Break"
                }[break_type]
                st.write(f"- {break_name}: {start_time}-{end_time}")
            
            cols = st.columns(2)
            if is_active:
                if cols[0].button("Deactivate", key=f"deact_{template_id}"):
                    if toggle_template(template_id, False):
                        st.success("Template deactivated!")
                        st.rerun()
            else:
                if cols[0].button("Activate", key=f"act_{template_id}"):
                    if toggle_template(template_id, True):
                        st.success("Template activated!")
                        st.rerun()
    
    # View all bookings
    st.subheader("View Bookings")
    selected_date = st.date_input("Select Date", value=datetime.now().date())
    
    # Get all users
    users = get_all_users()
    for user in users:
        uid, username, role = user
        if role == "agent":
            bookings = get_agent_bookings(username, selected_date.strftime("%Y-%m-%d"))
            if bookings:
                st.write(f"**{username}**")
                for booking in bookings:
                    booking_id, _, _, _, _, _, template_name, break_type, start_time, end_time = booking
                    break_name = {
                        "first_tea": "First Tea Break",
                        "lunch": "Lunch Break",
                        "second_tea": "Second Tea Break"
                    }[break_type]
                    st.write(f"- {break_name} ({start_time}-{end_time}) - {template_name}")

if __name__ == "__main__":
    st.write("Request Management System")
