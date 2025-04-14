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

def get_requests():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
        return cursor.fetchall()
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

def get_group_messages():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_messages ORDER BY timestamp DESC LIMIT 50")
        return cursor.fetchall()
    finally:
        conn.close()
        
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
        
        # Create tables if they don't exist with proper error handling
        tables = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('agent', 'admin')))""",
                
            """CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                request_type TEXT,
                identifier TEXT,
                comment TEXT,
                timestamp TEXT,
                completed INTEGER DEFAULT 0)""",
                
            """CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_leader TEXT,
                agent_name TEXT,
                ticket_id TEXT,
                error_description TEXT,
                timestamp TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp TEXT,
                mentions TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS hold_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploader TEXT,
                image_data BLOB,
                timestamp TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS request_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                user TEXT,
                comment TEXT,
                timestamp TEXT,
                FOREIGN KEY(request_id) REFERENCES requests(id))""",
                
            """CREATE TABLE IF NOT EXISTS late_logins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                presence_time TEXT,
                login_time TEXT,
                reason TEXT,
                timestamp TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS quality_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                issue_type TEXT,
                timing TEXT,
                mobile_number TEXT,
                product TEXT,
                timestamp TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS midshift_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                issue_type TEXT,
                start_time TEXT,
                end_time TEXT,
                timestamp TEXT)""",
                
            """CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                killswitch_enabled INTEGER DEFAULT 0,
                chat_killswitch_enabled INTEGER DEFAULT 0)""",
                
            """CREATE TABLE IF NOT EXISTS break_settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                max_per_slot INTEGER DEFAULT 3,
                current_template TEXT DEFAULT 'default',
                active_templates TEXT DEFAULT '["default"]',
                template_states TEXT DEFAULT '{"default": "active"}')""",
                
            """CREATE TABLE IF NOT EXISTS break_templates (
                name TEXT PRIMARY KEY,
                description TEXT,
                shifts TEXT)"""
        ]
        
        for table in tables:
            try:
                cursor.execute(table)
            except sqlite3.OperationalError as e:
                st.error(f"Error creating table: {str(e)}")
                conn.rollback()
                continue
        
        # Check if system_settings exists and has all columns
        try:
            cursor.execute("SELECT killswitch_enabled, chat_killswitch_enabled FROM system_settings WHERE id = 1")
        except sqlite3.OperationalError:
            # Table exists but missing columns
            try:
                cursor.execute("ALTER TABLE system_settings ADD COLUMN chat_killswitch_enabled INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Ensure we have a row in system_settings
            cursor.execute("INSERT OR IGNORE INTO system_settings (id, killswitch_enabled, chat_killswitch_enabled) VALUES (1, 0, 0)")
        
        # Initialize break settings if empty
        cursor.execute("SELECT COUNT(*) FROM break_settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO break_settings (id, max_per_slot, current_template, active_templates, template_states)
                VALUES (1, 3, 'default', '["default"]', '{"default": "active"}')
            """)
            
            default_template = {
                "description": "Default break schedule",
                "shifts": {
                    "2pm": {
                        "early_tea": {"start": "15:00", "end": "16:30", "slots": ["15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"]},
                        "lunch": {"start": "18:30", "end": "20:30", "slots": ["18:30", "19:00", "19:30", "20:00", "20:30"]},
                        "late_tea": {"start": "20:45", "end": "21:30", "slots": ["20:45", "21:00", "21:15", "21:30"]},
                    },
                    "6pm": {
                        "early_tea": {"start": "19:00", "end": "20:45", "slots": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"]},
                        "lunch": {"start": "21:00", "end": "22:30", "slots": ["21:00", "21:30", "22:00", "22:30"]},
                        "late_tea": {"start": "00:00", "end": "01:30", "slots": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]},
                    }
                }
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO break_templates (name, description, shifts)
                VALUES (?, ?, ?)
            """, ("default", default_template["description"], json.dumps(default_template["shifts"])))
        
        # Create default admin account
        admin_accounts = [
            ("taha kirri", "arise@99", "admin"),
            ("Issam Samghini", "admin@2025", "admin"),
            ("Loubna Fellah", "admin@99", "admin"),
            ("Youssef Kamal", "admin@006", "admin"),
            ("Fouad Fathi", "admin@55", "admin")
        ]
        
        for username, password, role in admin_accounts:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (username, password, role) 
                    VALUES (?, ?, ?)
                """, (username, hash_password(password), role))
            except sqlite3.IntegrityError:
                pass 
        
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
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (username, password, role) 
                    VALUES (?, ?, ?)
                """, (agent_name, hash_password(workspace_id), "agent"))
            except sqlite3.IntegrityError:
                pass  # User already exists
        
        conn.commit()
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

# --------------------------
# Break Booking System Functions
# --------------------------

def load_break_settings():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT max_per_slot, current_template, active_templates, template_states FROM break_settings WHERE id = 1")
        result = cursor.fetchone()
        
        if result:
            max_per_slot, current_template, active_templates_json, template_states_json = result
            return {
                "max_per_slot": max_per_slot,
                "current_template": current_template,
                "active_templates": json.loads(active_templates_json),
                "template_states": json.loads(template_states_json)
            }
        else:
            # Return default settings if not found
            return {
                "max_per_slot": 3,
                "current_template": "default",
                "active_templates": ["default"],
                "template_states": {"default": "active"}
            }
    finally:
        conn.close()

def save_break_settings(settings):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE break_settings 
            SET max_per_slot = ?, current_template = ?, active_templates = ?, template_states = ?
            WHERE id = 1
        """, (
            settings["max_per_slot"],
            settings["current_template"],
            json.dumps(settings["active_templates"]),
            json.dumps(settings["template_states"])
        ))
        conn.commit()
    finally:
        conn.close()

def load_break_templates():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, description, shifts FROM break_templates")
        templates = {}
        for name, description, shifts_json in cursor.fetchall():
            templates[name] = {
                "description": description,
                "shifts": json.loads(shifts_json)
            }
        
        # Ensure at least default template exists
        if "default" not in templates:
            default_template = {
                "description": "Default break schedule",
                "shifts": {
                    "2pm": {
                        "early_tea": {"start": "15:00", "end": "16:30", "slots": ["15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"]},
                        "lunch": {"start": "18:30", "end": "20:30", "slots": ["18:30", "19:00", "19:30", "20:00", "20:30"]},
                        "late_tea": {"start": "20:45", "end": "21:30", "slots": ["20:45", "21:00", "21:15", "21:30"]},
                    },
                    "6pm": {
                        "early_tea": {"start": "19:00", "end": "20:45", "slots": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"]},
                        "lunch": {"start": "21:00", "end": "22:30", "slots": ["21:00", "21:30", "22:00", "22:30"]},
                        "late_tea": {"start": "00:00", "end": "01:30", "slots": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]},
                    }
                }
            }
            cursor.execute("""
                INSERT INTO break_templates (name, description, shifts)
                VALUES (?, ?, ?)
            """, ("default", default_template["description"], json.dumps(default_template["shifts"])))
            conn.commit()
            templates["default"] = default_template
        
        return templates
    finally:
        conn.close()

def save_break_template(name, description, shifts):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO break_templates (name, description, shifts)
            VALUES (?, ?, ?)
        """, (name, description, json.dumps(shifts)))
        conn.commit()
    finally:
        conn.close()

def delete_break_template(name):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM break_templates WHERE name = ?", (name,))
        conn.commit()
    finally:
        conn.close()

def get_current_break_template():
    settings = load_break_settings()
    templates = load_break_templates()
    
    # If the current_template doesn't exist, fall back to "default"
    if settings["current_template"] not in templates:
        settings["current_template"] = "default"
        save_break_settings(settings)
    
    return templates[settings["current_template"]]

def is_break_template_active(template_name):
    settings = load_break_settings()
    return template_name in settings["active_templates"]

def is_break_active(shift, break_type):
    settings = load_break_settings()
    current_template = get_current_break_template()
    
    # First check if the template is active
    if not is_break_template_active(settings["current_template"]):
        return False
        
    # Then check if the break exists in the current template
    if shift not in current_template["shifts"] or break_type not in current_template["shifts"][shift]:
        return False
        
    return True
    
def get_requests():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def safe_db_operation(operation):
    """Decorator for safe database operations"""
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                conn = get_db_connection()
                result = operation(conn, *args, **kwargs)
                return result
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    st.error(f"Database error: {str(e)}")
                    raise
            finally:
                if conn:
                    conn.close()
    return wrapper

@safe_db_operation
def add_break_booking(conn, agent_id, shift, break_type, slot, date):
    """Safely add a break booking with validation"""
    is_valid, message = validate_break_booking(agent_id, shift, break_type, slot, date)
    if not is_valid:
        st.error(message)
        return False
        
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO break_bookings (date, shift, break_type, slot, agent_id)
        VALUES (?, ?, ?, ?, ?)
    """, (date, shift, break_type, slot, agent_id))
    conn.commit()
    return cursor.rowcount > 0

def remove_break_booking(agent_id, shift, break_type, slot, date):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM break_bookings 
            WHERE date = ? AND shift = ? AND break_type = ? AND slot = ? AND agent_id = ?
        """, (date, shift, break_type, slot, agent_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def count_break_bookings(shift, break_type, slot, date):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM break_bookings
            WHERE date = ? AND shift = ? AND break_type = ? AND slot = ?
        """, (date, shift, break_type, slot))
        return cursor.fetchone()[0]
    finally:
        conn.close()

def get_agent_break_bookings(agent_id, date):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT shift, break_type, slot FROM break_bookings
            WHERE date = ? AND agent_id = ?
        """, (date, agent_id))
        
        agent_bookings = {"2pm": {}, "6pm": {}}
        for shift, break_type, slot in cursor.fetchall():
            if break_type not in agent_bookings[shift]:
                agent_bookings[shift][break_type] = []
            agent_bookings[shift][break_type].append(slot)
        
        return agent_bookings
    finally:
        conn.close()

def has_break_booking(agent_id, shift, break_type, date):
    agent_bookings = get_agent_break_bookings(agent_id, date)
    return break_type in agent_bookings[shift]

def clear_all_break_bookings():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM break_bookings")
        conn.commit()
    finally:
        conn.close()

def clear_break_bookings_for_date(date):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM break_bookings WHERE date = ?", (date,))
        conn.commit()
    finally:
        conn.close()

def validate_break_booking(agent_id, shift, break_type, slot, date):
    """Validate if a break booking is allowed"""
    # Check if date is not in the past
    booking_date = datetime.strptime(date, "%Y-%m-%d").date()
    if booking_date < datetime.now().date():
        return False, "Cannot book breaks for past dates"
    
    # Get agent's existing bookings
    agent_bookings = get_agent_break_bookings(agent_id, date)
    
    # Check for overlapping breaks
    booking_time = datetime.strptime(slot, "%H:%M").time()
    for existing_shift, breaks in agent_bookings.items():
        for existing_break, slots in breaks.items():
            for existing_slot in slots:
                existing_time = datetime.strptime(existing_slot, "%H:%M").time()
                # Check if times are within 30 minutes of each other
                time_diff = abs((datetime.combine(datetime.today(), booking_time) - 
                               datetime.combine(datetime.today(), existing_time)).total_seconds() / 60)
                if time_diff < 30:
                    return False, "Cannot book breaks within 30 minutes of each other"
    
    return True, "Valid booking"

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
# Break Booking Interface
# --------------------------

def break_booking_interface():
    st.header("Break Booking System")
    
    # Date selector
    date = st.date_input("Select Date", key="break_date_input")
    date_str = date.strftime("%Y-%m-%d")
    
    # Load current bookings for this agent
    agent_bookings = get_agent_break_bookings(st.session_state.username, date_str)
    
    # Get settings and templates
    settings = load_break_settings()
    templates = load_break_templates()
    
    # Get all active templates
    active_templates = settings.get("active_templates", [])
    if not active_templates:
        st.warning("No active break schedules available. Please check back later.")
        return
    
    max_per_slot = settings["max_per_slot"]
    
    # Create tabs for each active template
    template_tabs = st.tabs(active_templates)
    
    for i, template_name in enumerate(active_templates):
        with template_tabs[i]:
            st.subheader(f"{template_name} Break Schedule")
            
            # Get the template data
            template = templates[template_name]
            
            # Create tabs for the two shifts
            tab1, tab2 = st.tabs(["2:00 PM Shift", "6:00 PM Shift"])
            
            # 2 PM Shift
            with tab1:
                st.subheader("2:00 PM Shift")
                col1, col2, col3 = st.columns(3)
                
                # Early Tea Break
                if "early_tea" in template["shifts"]["2pm"]:
                    with col1:
                        st.markdown("### Early Tea Break")
                        early_tea_booked = "early_tea" in agent_bookings["2pm"]
                        
                        if early_tea_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['2pm']['early_tea'])}")
                            if st.button(f"Cancel Early Tea Booking (2PM) - {template_name}", key=f"cancel_early_tea_2pm_{template_name}"):
                                for slot in agent_bookings["2pm"]["early_tea"]:
                                    remove_break_booking(st.session_state.username, "2pm", "early_tea", slot, date_str)
                                st.rerun()
                        else:
                            early_tea_options = []
                            for slot in template["shifts"]["2pm"]["early_tea"]["slots"]:
                                count = count_break_bookings("2pm", "early_tea", slot, date_str)
                                if count < max_per_slot:
                                    early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if early_tea_options:
                                selected_early_tea = st.selectbox(f"Select Early Tea Time (2PM) - {template_name}", early_tea_options, key=f"early_tea_2pm_{template_name}")
                                if st.button(f"Book Early Tea Break (2PM) - {template_name}", key=f"book_early_tea_2pm_{template_name}"):
                                    slot = selected_early_tea.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "2pm", "early_tea", slot, date_str)
                                    if success:
                                        st.success(f"Booked Early Tea Break at {slot}")
                                        st.rerun()
                                    else:
                                        st.error("Booking failed. Please try again.")
                            else:
                                st.info("No available slots for Early Tea Break")
                
                # Lunch Break
                if "lunch" in template["shifts"]["2pm"]:
                    with col2:
                        st.markdown("### Lunch Break")
                        lunch_booked = "lunch" in agent_bookings["2pm"]
                        
                        if lunch_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['2pm']['lunch'])}")
                            if st.button(f"Cancel Lunch Booking (2PM) - {template_name}", key=f"cancel_lunch_2pm_{template_name}"):
                                for slot in agent_bookings["2pm"]["lunch"]:
                                    remove_break_booking(st.session_state.username, "2pm", "lunch", slot, date_str)
                                st.rerun()
                        else:
                            lunch_options = []
                            for slot in template["shifts"]["2pm"]["lunch"]["slots"]:
                                count = count_break_bookings("2pm", "lunch", slot, date_str)
                                if count < max_per_slot:
                                    lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if lunch_options:
                                selected_lunch = st.selectbox(f"Select Lunch Time (2PM) - {template_name}", lunch_options, key=f"lunch_2pm_{template_name}")
                                if st.button(f"Book Lunch Break (2PM) - {template_name}", key=f"book_lunch_2pm_{template_name}"):
                                    slot = selected_lunch.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "2pm", "lunch", slot, date_str)
                                    if success:
                                        st.success(f"Booked Lunch Break at {slot}")
                                        st.rerun()
                                    else:
                                        st.error("Booking failed. Please try again.")
                            else:
                                st.info("No available slots for Lunch Break")
                
                # Late Tea Break
                if "late_tea" in template["shifts"]["2pm"]:
                    with col3:
                        st.markdown("### Late Tea Break")
                        late_tea_booked = "late_tea" in agent_bookings["2pm"]
                        
                        if late_tea_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['2pm']['late_tea'])}")
                            if st.button(f"Cancel Late Tea Booking (2PM) - {template_name}", key=f"cancel_late_tea_2pm_{template_name}"):
                                for slot in agent_bookings["2pm"]["late_tea"]:
                                    remove_break_booking(st.session_state.username, "2pm", "late_tea", slot, date_str)
                                st.rerun()
                        else:
                            late_tea_options = []
                            for slot in template["shifts"]["2pm"]["late_tea"]["slots"]:
                                count = count_break_bookings("2pm", "late_tea", slot, date_str)
                                if count < max_per_slot:
                                    late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if late_tea_options:
                                selected_late_tea = st.selectbox(f"Select Late Tea Time (2PM) - {template_name}", late_tea_options, key=f"late_tea_2pm_{template_name}")
                                if st.button(f"Book Late Tea Break (2PM) - {template_name}", key=f"book_late_tea_2pm_{template_name}"):
                                    slot = selected_late_tea.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "2pm", "late_tea", slot, date_str)
                                    if success:
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
                if "early_tea" in template["shifts"]["6pm"]:
                    with col1:
                        st.markdown("### Early Tea Break")
                        early_tea_booked = "early_tea" in agent_bookings["6pm"]
                        
                        if early_tea_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['6pm']['early_tea'])}")
                            if st.button(f"Cancel Early Tea Booking (6PM) - {template_name}", key=f"cancel_early_tea_6pm_{template_name}"):
                                for slot in agent_bookings["6pm"]["early_tea"]:
                                    remove_break_booking(st.session_state.username, "6pm", "early_tea", slot, date_str)
                                st.rerun()
                        else:
                            early_tea_options = []
                            for slot in template["shifts"]["6pm"]["early_tea"]["slots"]:
                                count = count_break_bookings("6pm", "early_tea", slot, date_str)
                                if count < max_per_slot:
                                    early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if early_tea_options:
                                selected_early_tea = st.selectbox(f"Select Early Tea Time (6PM) - {template_name}", early_tea_options, key=f"early_tea_6pm_{template_name}")
                                if st.button(f"Book Early Tea Break (6PM) - {template_name}", key=f"book_early_tea_6pm_{template_name}"):
                                    slot = selected_early_tea.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "6pm", "early_tea", slot, date_str)
                                    if success:
                                        st.success(f"Booked Early Tea Break at {slot}")
                                        st.rerun()
                                    else:
                                        st.error("Booking failed. Please try again.")
                            else:
                                st.info("No available slots for Early Tea Break")
                
                # Lunch Break
                if "lunch" in template["shifts"]["6pm"]:
                    with col2:
                        st.markdown("### Lunch Break")
                        lunch_booked = "lunch" in agent_bookings["6pm"]
                        
                        if lunch_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['6pm']['lunch'])}")
                            if st.button(f"Cancel Lunch Booking (6PM) - {template_name}", key=f"cancel_lunch_6pm_{template_name}"):
                                for slot in agent_bookings["6pm"]["lunch"]:
                                    remove_break_booking(st.session_state.username, "6pm", "lunch", slot, date_str)
                                st.rerun()
                        else:
                            lunch_options = []
                            for slot in template["shifts"]["6pm"]["lunch"]["slots"]:
                                count = count_break_bookings("6pm", "lunch", slot, date_str)
                                if count < max_per_slot:
                                    lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if lunch_options:
                                selected_lunch = st.selectbox(f"Select Lunch Time (6PM) - {template_name}", lunch_options, key=f"lunch_6pm_{template_name}")
                                if st.button(f"Book Lunch Break (6PM) - {template_name}", key=f"book_lunch_6pm_{template_name}"):
                                    slot = selected_lunch.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "6pm", "lunch", slot, date_str)
                                    if success:
                                        st.success(f"Booked Lunch Break at {slot}")
                                        st.rerun()
                                    else:
                                        st.error("Booking failed. Please try again.")
                            else:
                                st.info("No available slots for Lunch Break")
                
                # Late Tea Break
                if "late_tea" in template["shifts"]["6pm"]:
                    with col3:
                        st.markdown("### Late Tea Break")
                        late_tea_booked = "late_tea" in agent_bookings["6pm"]
                        
                        if late_tea_booked:
                            st.success(f"Booked: {', '.join(agent_bookings['6pm']['late_tea'])}")
                            if st.button(f"Cancel Late Tea Booking (6PM) - {template_name}", key=f"cancel_late_tea_6pm_{template_name}"):
                                for slot in agent_bookings["6pm"]["late_tea"]:
                                    remove_break_booking(st.session_state.username, "6pm", "late_tea", slot, date_str)
                                st.rerun()
                        else:
                            late_tea_options = []
                            for slot in template["shifts"]["6pm"]["late_tea"]["slots"]:
                                count = count_break_bookings("6pm", "late_tea", slot, date_str)
                                if count < max_per_slot:
                                    late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                            
                            if late_tea_options:
                                selected_late_tea = st.selectbox(f"Select Late Tea Time (6PM) - {template_name}", late_tea_options, key=f"late_tea_6pm_{template_name}")
                                if st.button(f"Book Late Tea Break (6PM) - {template_name}", key=f"book_late_tea_6pm_{template_name}"):
                                    slot = selected_late_tea.split(" ")[0]  # Extract time from display format
                                    success = add_break_booking(st.session_state.username, "6pm", "late_tea", slot, date_str)
                                    if success:
                                        st.success(f"Booked Late Tea Break at {slot}")
                                        st.rerun()
                                    else:
                                        st.error("Booking failed. Please try again.")
                            else:
                                st.info("No available slots for Late Tea Break")

# --------------------------
# Break Booking Admin Interface
# --------------------------

def break_booking_admin_interface():
    st.header("Break Booking System - Admin View")
    
    # Load settings and templates
    settings = load_break_settings()
    templates = load_break_templates()
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4 = st.tabs(["View Bookings", "Manage Templates", "Settings", "Template Activation"])
    
    # Tab 1: View Bookings
    with tab1:
        st.subheader("View All Bookings")
        
        # Date selector
        date = st.date_input("Select Date to View", key="view_date_selector")
        date_str = date.strftime("%Y-%m-%d")
        
        # Get current template
        current_template = get_current_break_template()
        
        # Get all bookings for the selected date
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT shift, break_type, slot, agent_id 
                FROM break_bookings 
                WHERE date = ?
                ORDER BY shift, break_type, slot
            """, (date_str,))
            bookings_data = cursor.fetchall()
            
            # Organize bookings by shift and break type
            bookings = {"2pm": {}, "6pm": {}}
            for shift, break_type, slot, agent_id in bookings_data:
                if break_type not in bookings[shift]:
                    bookings[shift][break_type] = {}
                if slot not in bookings[shift][break_type]:
                    bookings[shift][break_type][slot] = []
                bookings[shift][break_type][slot].append(agent_id)
            
            # Create dataframes for each shift and break type
            if bookings_data:
                # 2 PM Shift
                st.markdown("### 2:00 PM Shift")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### Early Tea Break")
                    if "early_tea" in bookings["2pm"]:
                        early_tea_data = []
                        for slot in current_template["shifts"]["2pm"]["early_tea"]["slots"]:
                            if slot in bookings["2pm"]["early_tea"]:
                                for agent in bookings["2pm"]["early_tea"][slot]:
                                    early_tea_data.append({"Time": slot, "Agent ID": agent})
                        
                        if early_tea_data:
                            early_tea_df = pd.DataFrame(early_tea_data)
                            st.dataframe(early_tea_df)
                        else:
                            st.info("No bookings for Early Tea Break")
                    else:
                        st.info("No bookings for Early Tea Break")
                
                with col2:
                    st.markdown("#### Lunch Break")
                    if "lunch" in bookings["2pm"]:
                        lunch_data = []
                        for slot in current_template["shifts"]["2pm"]["lunch"]["slots"]:
                            if slot in bookings["2pm"]["lunch"]:
                                for agent in bookings["2pm"]["lunch"][slot]:
                                    lunch_data.append({"Time": slot, "Agent ID": agent})
                        
                        if lunch_data:
                            lunch_df = pd.DataFrame(lunch_data)
                            st.dataframe(lunch_df)
                        else:
                            st.info("No bookings for Lunch Break")
                    else:
                        st.info("No bookings for Lunch Break")
                
                with col3:
                    st.markdown("#### Late Tea Break")
                    if "late_tea" in bookings["2pm"]:
                        late_tea_data = []
                        for slot in current_template["shifts"]["2pm"]["late_tea"]["slots"]:
                            if slot in bookings["2pm"]["late_tea"]:
                                for agent in bookings["2pm"]["late_tea"][slot]:
                                    late_tea_data.append({"Time": slot, "Agent ID": agent})
                        
                        if late_tea_data:
                            late_tea_df = pd.DataFrame(late_tea_data)
                            st.dataframe(late_tea_df)
                        else:
                            st.info("No bookings for Late Tea Break")
                    else:
                        st.info("No bookings for Late Tea Break")
                
                # 6 PM Shift
                st.markdown("### 6:00 PM Shift")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("#### Early Tea Break")
                    if "early_tea" in bookings["6pm"]:
                        early_tea_data = []
                        for slot in current_template["shifts"]["6pm"]["early_tea"]["slots"]:
                            if slot in bookings["6pm"]["early_tea"]:
                                for agent in bookings["6pm"]["early_tea"][slot]:
                                    early_tea_data.append({"Time": slot, "Agent ID": agent})
                        
                        if early_tea_data:
                            early_tea_df = pd.DataFrame(early_tea_data)
                            st.dataframe(early_tea_df)
                        else:
                            st.info("No bookings for Early Tea Break")
                    else:
                        st.info("No bookings for Early Tea Break")
                
                with col2:
                    st.markdown("#### Lunch Break")
                    if "lunch" in bookings["6pm"]:
                        lunch_data = []
                        for slot in current_template["shifts"]["6pm"]["lunch"]["slots"]:
                            if slot in bookings["6pm"]["lunch"]:
                                for agent in bookings["6pm"]["lunch"][slot]:
                                    lunch_data.append({"Time": slot, "Agent ID": agent})
                        
                        if lunch_data:
                            lunch_df = pd.DataFrame(lunch_data)
                            st.dataframe(lunch_df)
                        else:
                            st.info("No bookings for Lunch Break")
                    else:
                        st.info("No bookings for Lunch Break")
                
                with col3:
                    st.markdown("#### Late Tea Break")
                    if "late_tea" in bookings["6pm"]:
                        late_tea_data = []
                        for slot in current_template["shifts"]["6pm"]["late_tea"]["slots"]:
                            if slot in bookings["6pm"]["late_tea"]:
                                for agent in bookings["6pm"]["late_tea"][slot]:
                                    late_tea_data.append({"Time": slot, "Agent ID": agent})
                        
                        if late_tea_data:
                            late_tea_df = pd.DataFrame(late_tea_data)
                            st.dataframe(late_tea_df)
                        else:
                            st.info("No bookings for Late Tea Break")
                    else:
                        st.info("No bookings for Late Tea Break")
                
                # Clear bookings button
                if st.button("Clear All Bookings for Selected Date"):
                    clear_break_bookings_for_date(date_str)
                    st.success(f"All bookings for {date_str} have been cleared!")
                    st.rerun()
            else:
                st.info(f"No bookings found for {date_str}")
        finally:
            conn.close()
    
    # Tab 2: Manage Templates
    with tab2:
        st.subheader("Manage Break Templates")
        
        # Display current template
        current_template_name = settings["current_template"]
        current_template = templates[current_template_name]
        
        st.markdown(f"**Current Template:** {current_template_name}")
        st.markdown(f"**Description:** {current_template.get('description', 'No description')}")
        
        # Template selector
        template_names = list(templates.keys())
        selected_template = st.selectbox("Select Template", template_names, 
                                       index=template_names.index(current_template_name),
                                       key="template_selector")
        
        if st.button("Set as Active Template"):
            settings["current_template"] = selected_template
            save_break_settings(settings)
            st.success(f"Template '{selected_template}' is now active!")
            st.rerun()
        
        # Create new template
        st.markdown("### Create New Template")
        new_template_name = st.text_input("New Template Name", key="new_template_name")
        new_template_description = st.text_input("Description", key="new_template_description")
        
        # Copy from existing template
        copy_from = st.selectbox("Copy settings from", template_names, key="copy_from_template")
        
        if st.button("Create New Template", key="create_new_template"):
            if new_template_name in templates:
                st.error("A template with this name already exists!")
            elif not new_template_name:
                st.error("Please enter a template name")
            else:
                # Create new template based on selected template
                new_template = {
                    "description": new_template_description,
                    "shifts": templates[copy_from]["shifts"]
                }
                save_break_template(new_template_name, new_template_description, new_template["shifts"])
                st.success(f"Template '{new_template_name}' created!")
                st.rerun()
        
        # Edit existing template
        st.markdown("### Edit Template Breaks")
        edit_template = st.selectbox("Select template to edit", template_names, key="edit_template_selector")
        
        if edit_template in templates:
            template_to_edit = templates[edit_template]
            
            st.markdown(f"#### Editing: {edit_template}")
            
            shift_to_edit = st.selectbox("Select Shift", ["2pm", "6pm"], key="edit_shift_selector")
            break_to_edit = st.selectbox("Select Break Type", ["early_tea", "lunch", "late_tea"], key="edit_break_selector")
            
            # Get current slots for the selected break
            current_slots = template_to_edit["shifts"][shift_to_edit][break_to_edit]["slots"]
            st.write("Current Slots:")
            st.write(", ".join(current_slots))
            
            # Edit slots
            new_slots = st.text_area("Edit Break Slots (comma-separated times)", 
                                    value=", ".join(current_slots), key="edit_slots_textarea")
            
            if st.button("Update Template Breaks", key="update_template_breaks"):
                try:
                    # Parse and validate slots
                    slots_list = [slot.strip() for slot in new_slots.split(",")]
                    
                    # Simple validation of time format
                    for slot in slots_list:
                        # Check if time format is valid (HH:MM)
                        parts = slot.split(":")
                        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                            raise ValueError(f"Invalid time format: {slot}")
                        
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        
                        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
                            raise ValueError(f"Invalid time: {slot}")
                    
                    # Update template
                    template_to_edit["shifts"][shift_to_edit][break_to_edit]["slots"] = slots_list
                    save_break_template(edit_template, template_to_edit["description"], template_to_edit["shifts"])
                    st.success(f"Slots updated for {edit_template}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating slots: {str(e)}")
        
        # Delete template
        st.markdown("### Delete Template")
        if len(templates) > 1:  # Don't allow deleting the last template
            template_to_delete = st.selectbox("Select template to delete", 
                                            [t for t in template_names if t != "default"],
                                            key="delete_template_selector")
            
            if st.button("Delete Template", key="delete_template_button", type="primary"):
                if template_to_delete == settings["current_template"]:
                    st.error("Cannot delete the active template. Please select another template first.")
                else:
                    delete_break_template(template_to_delete)
                    st.success(f"Template '{template_to_delete}' deleted!")
                    st.rerun()
        else:
            st.info("Cannot delete the only remaining template")
    
    # Tab 3: Settings
    with tab3:
        st.subheader("System Settings")
        
        # Max bookings per slot
        max_per_slot = st.number_input("Maximum Bookings Per Slot", 
                                       min_value=1, 
                                       max_value=20, 
                                       value=settings["max_per_slot"],
                                       key="max_per_slot_input")
        
        if st.button("Update Max Bookings", key="update_max_bookings"):
            settings["max_per_slot"] = int(max_per_slot)
            save_break_settings(settings)
            st.success(f"Maximum bookings per slot updated to {max_per_slot}!")
            st.rerun()
        
        # Clear all bookings
        st.markdown("### Clear All Bookings")
        st.warning("This will delete ALL bookings from the system!")
        if st.button("Clear All Bookings", key="clear_all_bookings", type="primary"):
            clear_all_break_bookings()
            st.success("All bookings have been cleared!")
    
    # Tab 4: Template Activation
    with tab4:
        st.subheader("Template Activation Management")
        st.info("Activate or deactivate entire break templates")
        
        # Display current active templates
        st.markdown("### Current Active Templates")
        active_templates = settings.get("active_templates", [])
        if active_templates:
            st.write(", ".join(active_templates))
        else:
            st.warning("No templates are currently active!")
        
        # Template activation controls
        st.markdown("### Manage Template States")
        template_names = list(templates.keys())
        
        for template_name in template_names:
            current_state = settings["template_states"].get(template_name, "standby")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{template_name}**")
                st.caption(templates[template_name].get("description", "No description"))
            
            with col2:
                new_state = st.selectbox(
                    f"State for {template_name}",
                    ["active", "standby"],
                    index=0 if current_state == "active" else 1,
                    key=f"template_state_{template_name}"
                )
                
                if new_state != current_state:
                    if st.button(f"Update {template_name}", key=f"update_state_{template_name}"):
                        settings["template_states"][template_name] = new_state
                        
                        # Update active templates list
                        if new_state == "active" and template_name not in settings["active_templates"]:
                            settings["active_templates"].append(template_name)
                        elif new_state == "standby" and template_name in settings["active_templates"]:
                            settings["active_templates"].remove(template_name)
                        
                        save_break_settings(settings)
                        st.success(f"Template '{template_name}' state updated to {new_state}!")
                        st.rerun()
        
        # Warning if current template is in standby
        if settings["current_template"] not in settings["active_templates"]:
            st.warning(f"Current template '{settings['current_template']}' is in standby mode and won't be available to agents.")

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

def init_session_state():
    """Safely initialize session state"""
    if "authenticated" not in st.session_state:
        default_state = {
            "authenticated": False,
            "role": None,
            "username": None,
            "current_section": "requests",
            "last_request_count": 0,
            "last_mistake_count": 0,
            "last_message_ids": [],
            "break_templates": {},
            "active_template": None
        }
        
        try:
            # Try to get counts from database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM requests")
            default_state["last_request_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mistakes")
            default_state["last_mistake_count"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT id FROM group_messages ORDER BY timestamp DESC LIMIT 50")
            default_state["last_message_ids"] = [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error:
            # Use default values if database access fails
            pass
        finally:
            if 'conn' in locals():
                conn.close()
                
        st.session_state.update(default_state)

init_session_state()

if "authenticated" not in st.session_state:
    try:
        st.session_state.update({
            "authenticated": False,
            "role": None,
            "username": None,
            "current_section": "requests",
            "last_request_count": len(get_requests()) if 'get_requests' in globals() else 0,
            "last_mistake_count": len(get_mistakes()) if 'get_mistakes' in globals() else 0,
            "last_message_ids": [msg[0] for msg in get_group_messages()] if 'get_group_messages' in globals() else []
        })
    except Exception as e:
        st.session_state.update({
            "authenticated": False,
            "role": None,
            "username": None,
            "current_section": "requests",
            "last_request_count": 0,
            "last_mistake_count": 0,
            "last_message_ids": []
        })
        st.error(f"Initialization error: {str(e)}")

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

    elif st.session_state.current_section == "break_booking":
        break_booking_interface()

    elif st.session_state.current_section == "break_admin":
        if st.session_state.role == "admin":
            break_booking_admin_interface()
        else:
            st.warning("You don't have permission to access this section.")

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

def validate_break_template(template):
    """Validate break template structure and timing"""
    try:
        for shift in ["2pm", "6pm"]:
            if shift not in template["shifts"]:
                return False, f"Missing shift: {shift}"
                
            shift_data = template["shifts"][shift]
            last_end_time = None
            
            for break_type in ["early_tea", "lunch", "late_tea"]:
                if break_type not in shift_data:
                    continue
                    
                break_data = shift_data[break_type]
                if "slots" not in break_data:
                    return False, f"Missing slots for {break_type} in {shift}"
                    
                # Validate slot times are in order
                slots = break_data["slots"]
                for i in range(len(slots)-1):
                    time1 = datetime.strptime(slots[i], "%H:%M").time()
                    time2 = datetime.strptime(slots[i+1], "%H:%M").time()
                    if time1 >= time2:
                        return False, f"Slots must be in chronological order: {slots[i]} >= {slots[i+1]}"
                        
                # Check break periods don't overlap
                if last_end_time:
                    first_time = datetime.strptime(slots[0], "%H:%M").time()
                    if last_end_time >= first_time:
                        return False, "Break periods overlap"
                        
                last_end_time = datetime.strptime(slots[-1], "%H:%M").time()
                
        return True, "Template is valid"
    except Exception as e:
        return False, f"Template validation error: {str(e)}"

def safe_delete_template(template_name):
    """Safely delete a template with validation"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check for active bookings
        cursor.execute("""
            SELECT COUNT(*) FROM break_bookings b
            JOIN break_templates t ON b.template_name = t.name
            WHERE t.name = ? AND b.date >= date('now')
        """, (template_name,))
        
        active_bookings = cursor.fetchone()[0]
        if active_bookings > 0:
            return False, f"Cannot delete template: {active_bookings} active bookings exist"
            
        # Delete template
        cursor.execute("DELETE FROM break_templates WHERE name = ?", (template_name,))
        conn.commit()
        return True, "Template deleted successfully"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

if __name__ == "__main__":
    st.write("Request Management System")
