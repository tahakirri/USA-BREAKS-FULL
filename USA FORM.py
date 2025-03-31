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
import plotly.graph_objects as go
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("plotly")

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
        cursor.execute("SELECT role, team FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", 
                      (username, hashed_password))
        result = cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)
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
                role TEXT CHECK(role IN ('agent', 'admin', 'team_leader')),
                team TEXT,
                skillset TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT,
                request_type TEXT,
                identifier TEXT,
                comment TEXT,
                timestamp TEXT,
                completed INTEGER DEFAULT 0,
                team TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_leader TEXT,
                agent_name TEXT,
                ticket_id TEXT,
                error_description TEXT,
                timestamp TEXT,
                team TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp TEXT,
                mentions TEXT,
                team TEXT,
                skillset TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hold_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploader TEXT,
                image_data BLOB,
                timestamp TEXT,
                team TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_breaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT,
                date TEXT,
                agent_id TEXT,
                lunch_break TEXT,
                early_tea TEXT,
                late_tea TEXT,
                UNIQUE(team, date, agent_id))
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_break_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT,
                lunch_breaks TEXT,
                early_tea_breaks TEXT,
                late_tea_breaks TEXT)
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_break_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT,
                break_type TEXT,
                time_slot TEXT,
                max_limit INTEGER)
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
            INSERT OR IGNORE INTO users (username, password, role, team) 
            VALUES (?, ?, ?, ?)
        """, ("taha kirri", hash_password("arise@99"), "admin", "admin"))
        
        admin_accounts = [
            ("taha kirri", "arise@99", "admin", "admin"),
            ("Issam Samghini", "admin@2025", "admin", "admin"),
            ("Loubna Fellah", "admin@99", "admin", "admin"),
            ("Youssef Kamal", "admin@006", "admin", "admin"),
            ("Fouad Fathi", "admin@55", "admin", "admin")
        ]
        
        for username, password, role, team in admin_accounts:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role, team) 
                VALUES (?, ?, ?, ?)
            """, (username, hash_password(password), role, team))
        
        # Create agent accounts with teams
        agents = [
            ("Karabila Younes", "30866", "agent", "Team A"),
            ("Kaoutar Mzara", "30514", "agent", "Team A"),
            ("Ben Tahar Chahid", "30864", "agent", "Team A"),
            ("Cherbassi Khadija", "30868", "agent", "Team B"),
            ("Lekhmouchi Kamal", "30869", "agent", "Team B"),
            ("Said Kilani", "30626", "agent", "Team B"),
            ("AGLIF Rachid", "30830", "agent", "Team C"),
            ("Yacine Adouha", "30577", "agent", "Team C"),
            ("Manal Elanbi", "30878", "agent", "Team C"),
            ("Jawad Ouassaddine", "30559", "agent", "Team D"),
            ("Kamal Elhaouar", "30844", "agent", "Team D"),
            ("Hoummad Oubella", "30702", "agent", "Team D"),
            ("Zouheir Essafi", "30703", "agent", "Team E"),
            ("Anwar Atifi", "30781", "agent", "Team E"),
            ("Said Elgaouzi", "30782", "agent", "Team E"),
            ("HAMZA SAOUI", "30716", "agent", "Team F"),
            ("Ibtissam Mazhari", "30970", "agent", "Team F"),
            ("Imad Ghazali", "30971", "agent", "Team F"),
            ("Jamila Lahrech", "30972", "agent", "Team G"),
            ("Nassim Ouazzani Touhami", "30973", "agent", "Team G"),
            ("Salaheddine Chaggour", "30974", "agent", "Team G"),
            ("Omar Tajani", "30711", "agent", "Team H"),
            ("Nizar Remz", "30728", "agent", "Team H"),
            ("Abdelouahed Fettah", "30693", "agent", "Team H"),
            ("Amal Bouramdane", "30675", "agent", "Team I"),
            ("Fatima Ezzahrae Oubaalla", "30513", "agent", "Team I"),
            ("Redouane Bertal", "30643", "agent", "Team I"),
            ("Abdelouahab Chenani", "30789", "agent", "Team J"),
            ("Imad El Youbi", "30797", "agent", "Team J"),
            ("Youssef Hammouda", "30791", "agent", "Team J"),
            ("Anas Ouassifi", "30894", "agent", "Team K"),
            ("SALSABIL ELMOUSS", "30723", "agent", "Team K"),
            ("Hicham Khalafa", "30712", "agent", "Team K"),
            ("Ghita Adib", "30710", "agent", "Team L"),
            ("Aymane Msikila", "30722", "agent", "Team L"),
            ("Marouane Boukhadda", "30890", "agent", "Team L"),
            ("Hamid Boulatouan", "30899", "agent", "Team M"),
            ("Bouchaib Chafiqi", "30895", "agent", "Team M"),
            ("Houssam Gouaalla", "30891", "agent", "Team M"),
            ("Abdellah Rguig", "30963", "agent", "Team N"),
            ("Abdellatif Chatir", "30964", "agent", "Team N"),
            ("Abderrahman Oueto", "30965", "agent", "Team N"),
            ("Fatiha Lkamel", "30967", "agent", "Team O"),
            ("Abdelhamid Jaber", "30708", "agent", "Team O"),
            ("Yassine Elkanouni", "30735", "agent", "Team O")
        ]
        
        for agent_name, workspace_id, role, team in agents:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role, team) 
                VALUES (?, ?, ?, ?)
            """, (agent_name, hash_password(workspace_id), role, team))
        
        # Create team leaders
        team_leaders = [
            ("Team Leader A", "leader1", "team_leader", "Team A"),
            ("Team Leader B", "leader2", "team_leader", "Team B"),
            ("Team Leader C", "leader3", "team_leader", "Team C"),
            ("Team Leader D", "leader4", "team_leader", "Team D"),
            ("Team Leader E", "leader5", "team_leader", "Team E")
        ]
        
        for leader_name, password, role, team in team_leaders:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role, team) 
                VALUES (?, ?, ?, ?)
            """, (leader_name, hash_password(password), role, team))
        
        # Create default break templates for teams
        teams = ["Team A", "Team B", "Team C", "Team D", "Team E", "Team F", 
                "Team G", "Team H", "Team I", "Team J", "Team K", "Team L",
                "Team M", "Team N", "Team O"]
        
        for team in teams:
            # Check if template exists
            cursor.execute("SELECT id FROM team_break_templates WHERE team = ?", (team,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO team_break_templates (team, lunch_breaks, early_tea_breaks, late_tea_breaks)
                    VALUES (?, ?, ?, ?)
                """, (
                    team,
                    json.dumps(["19:30", "20:00", "20:30", "21:00", "21:30"]),
                    json.dumps(["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"]),
                    json.dumps(["21:45", "22:00", "22:15", "22:30"])
                ))
                
                # Add default limits
                for time_slot in ["19:30", "20:00", "20:30", "21:00", "21:30"]:
                    cursor.execute("""
                        INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                        VALUES (?, ?, ?, ?)
                    """, (team, "lunch", time_slot, 5))
                
                for time_slot in ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"]:
                    cursor.execute("""
                        INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                        VALUES (?, ?, ?, ?)
                    """, (team, "early_tea", time_slot, 3))
                
                for time_slot in ["21:45", "22:00", "22:15", "22:30"]:
                    cursor.execute("""
                        INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                        VALUES (?, ?, ?, ?)
                    """, (team, "late_tea", time_slot, 3))
        
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

def add_request(agent_name, request_type, identifier, comment, team):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO requests (agent_name, request_type, identifier, comment, timestamp, team) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agent_name, request_type, identifier, comment, timestamp, team))
        
        request_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO request_comments (request_id, user, comment, timestamp)
            VALUES (?, ?, ?, ?)
        """, (request_id, agent_name, f"Request created: {comment}", timestamp))
        
        conn.commit()
        return True
    finally:
        conn.close()

def get_requests(team=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("SELECT * FROM requests WHERE team = ? ORDER BY timestamp DESC", (team,))
        else:
            cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_requests(query, team=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        query = f"%{query.lower()}%"
        if team:
            cursor.execute("""
                SELECT * FROM requests 
                WHERE (LOWER(agent_name) LIKE ? 
                OR LOWER(request_type) LIKE ? 
                OR LOWER(identifier) LIKE ? 
                OR LOWER(comment) LIKE ?)
                AND team = ?
                ORDER BY timestamp DESC
            """, (query, query, query, query, team))
        else:
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

def add_mistake(team_leader, agent_name, ticket_id, error_description, team):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mistakes (team_leader, agent_name, ticket_id, error_description, timestamp, team) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (team_leader, agent_name, ticket_id, error_description,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), team))
        conn.commit()
        return True
    finally:
        conn.close()

def get_mistakes(team=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("SELECT * FROM mistakes WHERE team = ? ORDER BY timestamp DESC", (team,))
        else:
            cursor.execute("SELECT * FROM mistakes ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def search_mistakes(query, team=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        query = f"%{query.lower()}%"
        if team:
            cursor.execute("""
                SELECT * FROM mistakes 
                WHERE (LOWER(agent_name) LIKE ? 
                OR LOWER(ticket_id) LIKE ? 
                OR LOWER(error_description) LIKE ?)
                AND team = ?
                ORDER BY timestamp DESC
            """, (query, query, query, team))
        else:
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

def send_group_message(sender, message, team=None, skillset=None):
    if is_killswitch_enabled() or is_chat_killswitch_enabled():
        st.error("Chat is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        mentions = re.findall(r'@(\w+)', message)
        cursor.execute("""
            INSERT INTO group_messages (sender, message, timestamp, mentions, team, skillset) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sender, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             ','.join(mentions), team, skillset))
        conn.commit()
        return True
    finally:
        conn.close()

def get_group_messages(team=None, skillset=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team and skillset:
            cursor.execute("""
                SELECT * FROM group_messages 
                WHERE (team = ? OR team IS NULL) AND (skillset = ? OR skillset IS NULL)
                ORDER BY timestamp DESC LIMIT 50
            """, (team, skillset))
        elif team:
            cursor.execute("""
                SELECT * FROM group_messages 
                WHERE team = ? OR team IS NULL
                ORDER BY timestamp DESC LIMIT 50
            """, (team,))
        else:
            cursor.execute("SELECT * FROM group_messages ORDER BY timestamp DESC LIMIT 50")
        return cursor.fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, team FROM users")
        return cursor.fetchall()
    finally:
        conn.close()

def get_users_by_team(team):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE team = ?", (team,))
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def add_user(username, password, role, team=None, skillset=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, role, team, skillset) 
            VALUES (?, ?, ?, ?, ?)
        """, (username, hash_password(password), role, team, skillset))
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

def add_hold_image(uploader, image_data, team=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hold_images (uploader, image_data, timestamp, team) 
            VALUES (?, ?, ?, ?)
        """, (uploader, image_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), team))
        conn.commit()
        return True
    finally:
        conn.close()

def get_hold_images(team=None):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("SELECT * FROM hold_images WHERE team = ? ORDER BY timestamp DESC", (team,))
        else:
            cursor.execute("SELECT * FROM hold_images ORDER BY timestamp DESC")
        return cursor.fetchall()
    finally:
        conn.close()

def clear_hold_images(team=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("DELETE FROM hold_images WHERE team = ?", (team,))
        else:
            cursor.execute("DELETE FROM hold_images")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_requests(team=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("DELETE FROM requests WHERE team = ?", (team,))
            cursor.execute("""
                DELETE FROM request_comments 
                WHERE request_id IN (SELECT id FROM requests WHERE team = ?)
            """, (team,))
        else:
            cursor.execute("DELETE FROM requests")
            cursor.execute("DELETE FROM request_comments")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_mistakes(team=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team:
            cursor.execute("DELETE FROM mistakes WHERE team = ?", (team,))
        else:
            cursor.execute("DELETE FROM mistakes")
        conn.commit()
        return True
    finally:
        conn.close()

def clear_all_group_messages(team=None, skillset=None):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if team and skillset:
            cursor.execute("DELETE FROM group_messages WHERE team = ? AND skillset = ?", (team, skillset))
        elif team:
            cursor.execute("DELETE FROM group_messages WHERE team = ?", (team,))
        elif skillset:
            cursor.execute("DELETE FROM group_messages WHERE skillset = ?", (skillset,))
        else:
            cursor.execute("DELETE FROM group_messages")
        conn.commit()
        return True
    finally:
        conn.close()

def get_team_break_template(team):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT lunch_breaks, early_tea_breaks, late_tea_breaks FROM team_break_templates WHERE team = ?", (team,))
        result = cursor.fetchone()
        if result:
            return {
                "lunch_breaks": json.loads(result[0]),
                "tea_breaks": {
                    "early": json.loads(result[1]),
                    "late": json.loads(result[2])
                }
            }
        return None
    finally:
        conn.close()

def save_team_break_template(team, template):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO team_break_templates (team, lunch_breaks, early_tea_breaks, late_tea_breaks)
            VALUES (?, ?, ?, ?)
        """, (
            team,
            json.dumps(template["lunch_breaks"]),
            json.dumps(template["tea_breaks"]["early"]),
            json.dumps(template["tea_breaks"]["late"])
        ))
        conn.commit()
        return True
    finally:
        conn.close()

def get_team_break_limits(team):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT break_type, time_slot, max_limit FROM team_break_limits WHERE team = ?", (team,))
        results = cursor.fetchall()
        
        limits = {
            "lunch": {},
            "early_tea": {},
            "late_tea": {}
        }
        
        for break_type, time_slot, max_limit in results:
            if break_type == "lunch":
                limits["lunch"][time_slot] = max_limit
            elif break_type == "early_tea":
                limits["early_tea"][time_slot] = max_limit
            elif break_type == "late_tea":
                limits["late_tea"][time_slot] = max_limit
        
        return limits
    finally:
        conn.close()

def save_team_break_limits(team, limits):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        # First delete existing limits for this team
        cursor.execute("DELETE FROM team_break_limits WHERE team = ?", (team,))
        
        # Insert new limits
        for time_slot, max_limit in limits["lunch"].items():
            cursor.execute("""
                INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                VALUES (?, ?, ?, ?)
            """, (team, "lunch", time_slot, max_limit))
        
        for time_slot, max_limit in limits["early_tea"].items():
            cursor.execute("""
                INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                VALUES (?, ?, ?, ?)
            """, (team, "early_tea", time_slot, max_limit))
        
        for time_slot, max_limit in limits["late_tea"].items():
            cursor.execute("""
                INSERT INTO team_break_limits (team, break_type, time_slot, max_limit)
                VALUES (?, ?, ?, ?)
            """, (team, "late_tea", time_slot, max_limit))
        
        conn.commit()
        return True
    finally:
        conn.close()

def book_team_break(team, date, agent_id, break_type, time_slot):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        
        # First get current booking if exists
        cursor.execute("SELECT lunch_break, early_tea, late_tea FROM team_breaks WHERE team = ? AND date = ? AND agent_id = ?", 
                      (team, date, agent_id))
        result = cursor.fetchone()
        
        if result:
            lunch, early_tea, late_tea = result
            if break_type == "lunch":
                lunch = time_slot
            elif break_type == "early_tea":
                early_tea = time_slot
            elif break_type == "late_tea":
                late_tea = time_slot
            
            cursor.execute("""
                UPDATE team_breaks 
                SET lunch_break = ?, early_tea = ?, late_tea = ?
                WHERE team = ? AND date = ? AND agent_id = ?
            """, (lunch, early_tea, late_tea, team, date, agent_id))
        else:
            lunch = time_slot if break_type == "lunch" else None
            early_tea = time_slot if break_type == "early_tea" else None
            late_tea = time_slot if break_type == "late_tea" else None
            
            cursor.execute("""
                INSERT INTO team_breaks (team, date, agent_id, lunch_break, early_tea, late_tea)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (team, date, agent_id, lunch, early_tea, late_tea))
        
        conn.commit()
        return True
    finally:
        conn.close()

def cancel_team_break(team, date, agent_id, break_type):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        
        # First get current booking
        cursor.execute("SELECT lunch_break, early_tea, late_tea FROM team_breaks WHERE team = ? AND date = ? AND agent_id = ?", 
                      (team, date, agent_id))
        result = cursor.fetchone()
        
        if result:
            lunch, early_tea, late_tea = result
            if break_type == "lunch":
                lunch = None
            elif break_type == "early_tea":
                early_tea = None
            elif break_type == "late_tea":
                late_tea = None
            
            # If all breaks are None, delete the record
            if lunch is None and early_tea is None and late_tea is None:
                cursor.execute("""
                    DELETE FROM team_breaks 
                    WHERE team = ? AND date = ? AND agent_id = ?
                """, (team, date, agent_id))
            else:
                cursor.execute("""
                    UPDATE team_breaks 
                    SET lunch_break = ?, early_tea = ?, late_tea = ?
                    WHERE team = ? AND date = ? AND agent_id = ?
                """, (lunch, early_tea, late_tea, team, date, agent_id))
        
        conn.commit()
        return True
    finally:
        conn.close()

def get_team_break_bookings(team, date):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT agent_id, lunch_break, early_tea, late_tea FROM team_breaks WHERE team = ? AND date = ?", 
                      (team, date))
        return cursor.fetchall()
    finally:
        conn.close()

def count_team_break_bookings(team, date, break_type, time_slot):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        if break_type == "lunch":
            cursor.execute("""
                SELECT COUNT(*) FROM team_breaks 
                WHERE team = ? AND date = ? AND lunch_break = ?
            """, (team, date, time_slot))
        elif break_type == "early_tea":
            cursor.execute("""
                SELECT COUNT(*) FROM team_breaks 
                WHERE team = ? AND date = ? AND early_tea = ?
            """, (team, date, time_slot))
        elif break_type == "late_tea":
            cursor.execute("""
                SELECT COUNT(*) FROM team_breaks 
                WHERE team = ? AND date = ? AND late_tea = ?
            """, (team, date, time_slot))
        
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()

def get_agent_break_bookings(team, date, agent_id):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT lunch_break, early_tea, late_tea FROM team_breaks WHERE team = ? AND date = ? AND agent_id = ?", 
                      (team, date, agent_id))
        result = cursor.fetchone()
        if result:
            return {
                "lunch": result[0],
                "early_tea": result[1],
                "late_tea": result[2]
            }
        return None
    finally:
        conn.close()

def get_all_teams():
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT team FROM users WHERE team IS NOT NULL AND team != 'admin'")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def get_team_members(team):
    conn = sqlite3.connect("data/requests.db")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE team = ?", (team,))
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

def get_skillsets():
    return ["Technical", "Billing", "Retention", "General"]

# --------------------------
# Break Scheduling Functions
# --------------------------

def init_break_session_state():
    if 'current_template' not in st.session_state:
        st.session_state.current_template = None
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = datetime.now().strftime('%Y-%m-%d')
    if 'timezone_offset' not in st.session_state:
        st.session_state.timezone_offset = 0  # GMT by default

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
            "early": [adjust_time(t, offset) for t in template["tea_breaks"]["early"]],
            "late": [adjust_time(t, offset) for t in template["tea_breaks"]["late"]]
        }
    }
    return adjusted_template

def display_team_break_schedule(team, template):
    st.header(f"{team} Break Schedule")
    
    # Get current bookings
    bookings = get_team_break_bookings(team, st.session_state.selected_date)
    booking_counts = {
        "lunch": {},
        "early_tea": {},
        "late_tea": {}
    }
    
    # Initialize counts
    for time_slot in template["lunch_breaks"]:
        booking_counts["lunch"][time_slot] = 0
    
    for time_slot in template["tea_breaks"]["early"]:
        booking_counts["early_tea"][time_slot] = 0
    
    for time_slot in template["tea_breaks"]["late"]:
        booking_counts["late_tea"][time_slot] = 0
    
    # Count bookings
    for agent_id, lunch, early_tea, late_tea in bookings:
        if lunch:
            booking_counts["lunch"][lunch] += 1
        if early_tea:
            booking_counts["early_tea"][early_tea] += 1
        if late_tea:
            booking_counts["late_tea"][late_tea] += 1
    
    # Get break limits
    break_limits = get_team_break_limits(team)
    
    # Lunch breaks table
    st.markdown("### LUNCH BREAKS")
    lunch_data = []
    for time_slot in template["lunch_breaks"]:
        current = booking_counts["lunch"].get(time_slot, 0)
        limit = break_limits["lunch"].get(time_slot, 5)
        lunch_data.append({
            "Time": time_slot,
            "Booked": current,
            "Available": limit - current,
            "Status": "FULL" if current >= limit else "AVAILABLE"
        })
    
    lunch_df = pd.DataFrame(lunch_data)
    st.dataframe(lunch_df, hide_index=True)
    
    # Tea breaks tables
    st.markdown("### TEA BREAKS")
    
    # Early tea breaks
    st.markdown("#### Early Tea Breaks")
    early_tea_data = []
    for time_slot in template["tea_breaks"]["early"]:
        current = booking_counts["early_tea"].get(time_slot, 0)
        limit = break_limits["early_tea"].get(time_slot, 3)
        early_tea_data.append({
            "Time": time_slot,
            "Booked": current,
            "Available": limit - current,
            "Status": "FULL" if current >= limit else "AVAILABLE"
        })
    
    early_tea_df = pd.DataFrame(early_tea_data)
    st.dataframe(early_tea_df, hide_index=True)
    
    # Late tea breaks
    st.markdown("#### Late Tea Breaks")
    late_tea_data = []
    for time_slot in template["tea_breaks"]["late"]:
        current = booking_counts["late_tea"].get(time_slot, 0)
        limit = break_limits["late_tea"].get(time_slot, 3)
        late_tea_data.append({
            "Time": time_slot,
            "Booked": current,
            "Available": limit - current,
            "Status": "FULL" if current >= limit else "AVAILABLE"
        })
    
    late_tea_df = pd.DataFrame(late_tea_data)
    st.dataframe(late_tea_df, hide_index=True)
    
    # Visualizations
    st.markdown("### BREAK SCHEDULE VISUALIZATION")
    
    # Create a Gantt-style chart for breaks
    fig = go.Figure()
    
    # Add lunch breaks
    for time_slot in template["lunch_breaks"]:
        current = booking_counts["lunch"].get(time_slot, 0)
        limit = break_limits["lunch"].get(time_slot, 5)
        color = "red" if current >= limit else "green"
        
        fig.add_trace(go.Bar(
            x=[f"Lunch {time_slot}"],
            y=[current],
            name=f"Lunch {time_slot}",
            marker_color=color,
            text=f"{current}/{limit}",
            textposition='auto'
        ))
    
    # Add early tea breaks
    for time_slot in template["tea_breaks"]["early"]:
        current = booking_counts["early_tea"].get(time_slot, 0)
        limit = break_limits["early_tea"].get(time_slot, 3)
        color = "red" if current >= limit else "green"
        
        fig.add_trace(go.Bar(
            x=[f"Early Tea {time_slot}"],
            y=[current],
            name=f"Early Tea {time_slot}",
            marker_color=color,
            text=f"{current}/{limit}",
            textposition='auto'
        ))
    
    # Add late tea breaks
    for time_slot in template["tea_breaks"]["late"]:
        current = booking_counts["late_tea"].get(time_slot, 0)
        limit = break_limits["late_tea"].get(time_slot, 3)
        color = "red" if current >= limit else "green"
        
        fig.add_trace(go.Bar(
            x=[f"Late Tea {time_slot}"],
            y=[current],
            name=f"Late Tea {time_slot}",
            marker_color=color,
            text=f"{current}/{limit}",
            textposition='auto'
        ))
    
    fig.update_layout(
        title="Break Schedule Utilization",
        xaxis_title="Break Time",
        yaxis_title="Number of Agents",
        barmode='group',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

def admin_break_dashboard():
    st.title("Admin Break Dashboard")
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
    
    # Team selection
    teams = get_all_teams()
    selected_team = st.selectbox("Select Team:", teams)
    
    # Get team template
    template = get_team_break_template(selected_team)
    if not template:
        st.error("No break template found for this team. Please create one.")
        return
    
    # Date selection
    schedule_date = st.date_input("Select Date:", datetime.now())
    st.session_state.selected_date = schedule_date.strftime('%Y-%m-%d')
    
    # Display team schedule
    display_team_break_schedule(selected_team, template)
    
    # Team management
    st.markdown("---")
    st.header("Team Break Management")
    
    # Template editing
    with st.expander("Edit Break Template"):
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
        
        if st.button("Save Template"):
            new_template = {
                "lunch_breaks": [t.strip() for t in lunch_breaks.split("\n") if t.strip()],
                "tea_breaks": {
                    "early": [t.strip() for t in early_tea_breaks.split("\n") if t.strip()],
                    "late": [t.strip() for t in late_tea_breaks.split("\n") if t.strip()]
                }
            }
            save_team_break_template(selected_team, new_template)
            st.success("Template updated successfully!")
            st.rerun()
    
    # Break limits management
    with st.expander("Edit Break Limits"):
        break_limits = get_team_break_limits(selected_team)
        
        st.subheader("Lunch Break Limits")
        lunch_cols = st.columns(len(template["lunch_breaks"]))
        for i, time_slot in enumerate(template["lunch_breaks"]):
            with lunch_cols[i]:
                break_limits["lunch"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=break_limits["lunch"].get(time_slot, 5),
                    key=f"lunch_limit_{time_slot}"
                )
        
        st.subheader("Early Tea Break Limits")
        early_tea_cols = st.columns(len(template["tea_breaks"]["early"]))
        for i, time_slot in enumerate(template["tea_breaks"]["early"]):
            with early_tea_cols[i]:
                break_limits["early_tea"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=break_limits["early_tea"].get(time_slot, 3),
                    key=f"early_tea_limit_{time_slot}"
                )
        
        st.subheader("Late Tea Break Limits")
        late_tea_cols = st.columns(len(template["tea_breaks"]["late"]))
        for i, time_slot in enumerate(template["tea_breaks"]["late"]):
            with late_tea_cols[i]:
                break_limits["late_tea"][time_slot] = st.number_input(
                    f"Max at {time_slot}",
                    min_value=1,
                    value=break_limits["late_tea"].get(time_slot, 3),
                    key=f"late_tea_limit_{time_slot}"
                )
        
        if st.button("Save Break Limits"):
            save_team_break_limits(selected_team, break_limits)
            st.success("Break limits saved successfully!")
            st.rerun()
    
    # Bulk booking for team members
    with st.expander("Bulk Booking for Team"):
        st.warning("This will override existing bookings for selected agents")
        team_members = get_team_members(selected_team)
        selected_members = st.multiselect("Select Agents:", team_members)
        
        st.subheader("Lunch Break")
        lunch_time = st.selectbox("Select Lunch Time:", template["lunch_breaks"])
        
        st.subheader("Early Tea Break")
        early_tea_time = st.selectbox("Select Early Tea Time:", template["tea_breaks"]["early"])
        
        st.subheader("Late Tea Break")
        late_tea_time = st.selectbox("Select Late Tea Time:", template["tea_breaks"]["late"])
        
        if st.button("Apply Bulk Booking"):
            for agent in selected_members:
                book_team_break(selected_team, st.session_state.selected_date, agent, "lunch", lunch_time)
                book_team_break(selected_team, st.session_state.selected_date, agent, "early_tea", early_tea_time)
                book_team_break(selected_team, st.session_state.selected_date, agent, "late_tea", late_tea_time)
            st.success(f"Bookings applied to {len(selected_members)} agents!")
            st.rerun()

def team_leader_break_dashboard(team):
    st.title(f"{team} Break Dashboard")
    st.markdown("---")
    
    # Get team template
    template = get_team_break_template(team)
    if not template:
        st.error("No break template found for this team. Please contact admin.")
        return
    
    # Date selection
    schedule_date = st.date_input("Select Date:", datetime.now())
    st.session_state.selected_date = schedule_date.strftime('%Y-%m-%d')
    
    # Display team schedule
    display_team_break_schedule(team, template)
    
    # Individual booking management
    st.markdown("---")
    st.header("Individual Booking Management")
    
    team_members = get_team_members(team)
    selected_agent = st.selectbox("Select Agent:", team_members)
    
    # Get current bookings for agent
    current_bookings = get_agent_break_bookings(team, st.session_state.selected_date, selected_agent)
    
    # Lunch break booking
    st.subheader("Lunch Break")
    lunch_cols = st.columns(len(template["lunch_breaks"]))
    selected_lunch = current_bookings["lunch"] if current_bookings else None
    
    for i, time_slot in enumerate(template["lunch_breaks"]):
        with lunch_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "lunch", time_slot)
            limit = get_team_break_limits(team)["lunch"].get(time_slot, 5)
            
            if current >= limit and time_slot != selected_lunch:
                st.button(f"{time_slot} (FULL)", key=f"lunch_{time_slot}_{selected_agent}", disabled=True)
            else:
                if st.button(time_slot, key=f"lunch_{time_slot}_{selected_agent}"):
                    selected_lunch = time_slot
    
    # Early tea break booking
    st.subheader("Early Tea Break")
    early_tea_cols = st.columns(len(template["tea_breaks"]["early"]))
    selected_early_tea = current_bookings["early_tea"] if current_bookings else None
    
    for i, time_slot in enumerate(template["tea_breaks"]["early"]):
        with early_tea_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "early_tea", time_slot)
            limit = get_team_break_limits(team)["early_tea"].get(time_slot, 3)
            
            if current >= limit and time_slot != selected_early_tea:
                st.button(f"{time_slot} (FULL)", key=f"early_tea_{time_slot}_{selected_agent}", disabled=True)
            else:
                if st.button(time_slot, key=f"early_tea_{time_slot}_{selected_agent}"):
                    selected_early_tea = time_slot
    
    # Late tea break booking
    st.subheader("Late Tea Break")
    late_tea_cols = st.columns(len(template["tea_breaks"]["late"]))
    selected_late_tea = current_bookings["late_tea"] if current_bookings else None
    
    for i, time_slot in enumerate(template["tea_breaks"]["late"]):
        with late_tea_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "late_tea", time_slot)
            limit = get_team_break_limits(team)["late_tea"].get(time_slot, 3)
            
            if current >= limit and time_slot != selected_late_tea:
                st.button(f"{time_slot} (FULL)", key=f"late_tea_{time_slot}_{selected_agent}", disabled=True)
            else:
                if st.button(time_slot, key=f"late_tea_{time_slot}_{selected_agent}"):
                    selected_late_tea = time_slot
    
    # Save button
    if st.button("Save Bookings"):
        # Update lunch break
        if selected_lunch:
            book_team_break(team, st.session_state.selected_date, selected_agent, "lunch", selected_lunch)
        elif current_bookings and current_bookings["lunch"]:
            cancel_team_break(team, st.session_state.selected_date, selected_agent, "lunch")
        
        # Update early tea break
        if selected_early_tea:
            book_team_break(team, st.session_state.selected_date, selected_agent, "early_tea", selected_early_tea)
        elif current_bookings and current_bookings["early_tea"]:
            cancel_team_break(team, st.session_state.selected_date, selected_agent, "early_tea")
        
        # Update late tea break
        if selected_late_tea:
            book_team_break(team, st.session_state.selected_date, selected_agent, "late_tea", selected_late_tea)
        elif current_bookings and current_bookings["late_tea"]:
            cancel_team_break(team, st.session_state.selected_date, selected_agent, "late_tea")
        
        st.success("Bookings updated successfully!")
        st.rerun()

def agent_break_dashboard(team):
    st.title("Break Booking")
    st.markdown("---")
    
    # Use the logged-in username directly
    agent_id = st.session_state.username
    st.write(f"Booking breaks for: **{agent_id}**")
    
    # Get team template
    template = get_team_break_template(team)
    if not template:
        st.error("No break template found for your team. Please contact your team leader.")
        return
    
    # Date selection
    schedule_date = st.date_input("Select Date:", datetime.now())
    st.session_state.selected_date = schedule_date.strftime('%Y-%m-%d')
    
    # Get current bookings
    current_bookings = get_agent_break_bookings(team, st.session_state.selected_date, agent_id)
    
    # Get break limits
    break_limits = get_team_break_limits(team)
    
    # Booking section
    st.markdown("---")
    st.header("Available Break Slots")
    
    # Lunch break booking
    st.subheader("Lunch Break")
    lunch_cols = st.columns(len(template["lunch_breaks"]))
    selected_lunch = current_bookings["lunch"] if current_bookings else None
    
    for i, time_slot in enumerate(template["lunch_breaks"]):
        with lunch_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "lunch", time_slot)
            limit = break_limits["lunch"].get(time_slot, 5)
            
            if current >= limit and time_slot != selected_lunch:
                st.button(f"{time_slot} (FULL)", key=f"lunch_{time_slot}", disabled=True, help="This slot is full")
            elif time_slot == selected_lunch:
                if st.button(f"✅ {time_slot}", key=f"lunch_{time_slot}"):
                    cancel_team_break(team, st.session_state.selected_date, agent_id, "lunch")
                    st.rerun()
            else:
                if st.button(time_slot, key=f"lunch_{time_slot}"):
                    book_team_break(team, st.session_state.selected_date, agent_id, "lunch", time_slot)
                    st.rerun()
    
    # Tea break booking
    st.subheader("Tea Breaks")
    
    # Early tea breaks
    st.write("Early Tea Breaks:")
    early_tea_cols = st.columns(len(template["tea_breaks"]["early"]))
    selected_early_tea = current_bookings["early_tea"] if current_bookings else None
    
    for i, time_slot in enumerate(template["tea_breaks"]["early"]):
        with early_tea_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "early_tea", time_slot)
            limit = break_limits["early_tea"].get(time_slot, 3)
            
            if current >= limit and time_slot != selected_early_tea:
                st.button(f"{time_slot} (FULL)", key=f"early_tea_{time_slot}", disabled=True, help="This slot is full")
            elif time_slot == selected_early_tea:
                if st.button(f"✅ {time_slot}", key=f"early_tea_{time_slot}"):
                    cancel_team_break(team, st.session_state.selected_date, agent_id, "early_tea")
                    st.rerun()
            else:
                if st.button(time_slot, key=f"early_tea_{time_slot}"):
                    book_team_break(team, st.session_state.selected_date, agent_id, "early_tea", time_slot)
                    st.rerun()
    
    # Late tea breaks
    st.write("Late Tea Breaks:")
    late_tea_cols = st.columns(len(template["tea_breaks"]["late"]))
    selected_late_tea = current_bookings["late_tea"] if current_bookings else None
    
    for i, time_slot in enumerate(template["tea_breaks"]["late"]):
        with late_tea_cols[i]:
            current = count_team_break_bookings(team, st.session_state.selected_date, "late_tea", time_slot)
            limit = break_limits["late_tea"].get(time_slot, 3)
            
            if current >= limit and time_slot != selected_late_tea:
                st.button(f"{time_slot} (FULL)", key=f"late_tea_{time_slot}", disabled=True, help="This slot is full")
            elif time_slot == selected_late_tea:
                if st.button(f"✅ {time_slot}", key=f"late_tea_{time_slot}"):
                    cancel_team_break(team, st.session_state.selected_date, agent_id, "late_tea")
                    st.rerun()
            else:
                if st.button(time_slot, key=f"late_tea_{time_slot}"):
                    book_team_break(team, st.session_state.selected_date, agent_id, "late_tea", time_slot)
                    st.rerun()
    
    # Display current bookings
    if current_bookings and (current_bookings["lunch"] or current_bookings["early_tea"] or current_bookings["late_tea"]):
        st.markdown("---")
        st.header("Your Current Bookings")
        
        if current_bookings["lunch"]:
            st.write(f"**Lunch Break:** {current_bookings['lunch']}")
        
        if current_bookings["early_tea"]:
            st.write(f"**Early Tea Break:** {current_bookings['early_tea']}")
        
        if current_bookings["late_tea"]:
            st.write(f"**Late Tea Break:** {current_bookings['late_tea']}")
        
        if st.button("Cancel All Bookings"):
            if current_bookings["lunch"]:
                cancel_team_break(team, st.session_state.selected_date, agent_id, "lunch")
            if current_bookings["early_tea"]:
                cancel_team_break(team, st.session_state.selected_date, agent_id, "early_tea")
            if current_bookings["late_tea"]:
                cancel_team_break(team, st.session_state.selected_date, agent_id, "late_tea")
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
        .team-card {
            background: #1F2937;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 5px solid #3B82F6;
        }
        .skillset-tab {
            padding: 8px 15px;
            margin-right: 5px;
            border-radius: 20px;
            background: #374151;
            color: white;
            display: inline-block;
            cursor: pointer;
        }
        .skillset-tab.active {
            background: #3B82F6;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.update({
        "authenticated": False,
        "role": None,
        "username": None,
        "team": None,
        "current_section": "requests",
        "last_request_count": 0,
        "last_mistake_count": 0,
        "last_message_ids": [],
        "current_chat_skillset": None
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
                    role, team = authenticate(username, password)
                    if role:
                        st.session_state.update({
                            "authenticated": True,
                            "role": role,
                            "username": username,
                            "team": team,
                            "last_request_count": len(get_requests(team)),
                            "last_mistake_count": len(get_mistakes(team)),
                            "last_message_ids": [msg[0] for msg in get_group_messages(team)]
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
        current_requests = get_requests(st.session_state.team)
        current_mistakes = get_mistakes(st.session_state.team)
        current_messages = get_group_messages(st.session_state.team)
        
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
        st.markdown(f"**Team:** {st.session_state.team or 'N/A'}")
        st.markdown(f"**Role:** {st.session_state.role.capitalize()}")
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
                if value == "chat":
                    st.session_state.current_chat_skillset = None
                
        st.markdown("---")
        pending_requests = len([r for r in get_requests(st.session_state.team) if not r[6]])
        new_mistakes = len(get_mistakes(st.session_state.team))
        unread_messages = len([m for m in get_group_messages(st.session_state.team) 
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
                            if add_request(st.session_state.username, request_type, identifier, comment, st.session_state.team):
                                st.success("Request submitted successfully!")
                                st.rerun()
        
        st.subheader("🔍 Search Requests")
        search_query = st.text_input("Search requests...")
        requests = search_requests(search_query, st.session_state.team) if search_query else get_requests(st.session_state.team)
        
        st.subheader("All Requests")
        for req in requests:
            req_id, agent, req_type, identifier, comment, timestamp, completed, team = req
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
                    
                    if (st.session_state.role == "admin" or st.session_state.role == "team_leader") and not is_killswitch_enabled():
                        with st.form(key=f"comment_form_{req_id}"):
                            new_comment = st.text_input("Add status update/comment")
                            if st.form_submit_button("Add Comment"):
                                if new_comment:
                                    add_request_comment(req_id, st.session_state.username, new_comment)
                                    st.rerun()

    elif st.session_state.current_section == "dashboard":
        st.subheader("📊 Request Completion Dashboard")
        all_requests = get_requests(st.session_state.team)
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
        elif st.session_state.role == "team_leader":
            team_leader_break_dashboard(st.session_state.team)
        else:
            agent_break_dashboard(st.session_state.team)

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
                            add_mistake(st.session_state.username, agent_name, ticket_id, error_description, st.session_state.team)
        
        st.subheader("🔍 Search Mistakes")
        search_query = st.text_input("Search mistakes...")
        mistakes = search_mistakes(search_query, st.session_state.team) if search_query else get_mistakes(st.session_state.team)
        
        st.subheader("Mistakes Log")
        for mistake in mistakes:
            m_id, tl, agent, ticket, error, ts, team = mistake
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
            # Skillset tabs
            skillsets = get_skillsets()
            cols = st.columns(len(skillsets) + 1)
            
            for i, skillset in enumerate(skillsets):
                if cols[i].button(skillset, key=f"skillset_{skillset}"):
                    st.session_state.current_chat_skillset = skillset
            
            if cols[-1].button("All", key="skillset_all"):
                st.session_state.current_chat_skillset = None
            
            # Display messages
            messages = get_group_messages(st.session_state.team, st.session_state.current_chat_skillset)
            
            for msg in reversed(messages):
                msg_id, sender, message, ts, mentions, team, skillset = msg
                is_mentioned = st.session_state.username in (mentions.split(',') if mentions else [])
                st.markdown(f"""
                <div style="background-color: {'#3b82f6' if is_mentioned else '#1F1F1F'};
                            padding: 1rem;
                            border-radius: 8px;
                            margin-bottom: 1rem;">
                    <strong>{sender}</strong>{" (" + skillset + ")" if skillset else ""}: {message}<br>
                    <small>{ts}</small>
                </div>
                """, unsafe_allow_html=True)
            
            if not is_killswitch_enabled():
                with st.form("chat_form"):
                    message = st.text_input("Type your message...")
                    if st.form_submit_button("Send"):
                        if message:
                            send_group_message(
                                st.session_state.username, 
                                message, 
                                st.session_state.team,
                                st.session_state.current_chat_skillset
                            )
                            st.rerun()

    elif st.session_state.current_section == "hold":
        if (st.session_state.role == "admin" or st.session_state.role == "team_leader") and not is_killswitch_enabled():
            with st.expander("📤 Upload Image"):
                img = st.file_uploader("Choose image", type=["jpg", "png", "jpeg"])
                if img:
                    add_hold_image(st.session_state.username, img.read(), st.session_state.team)
        
        images = get_hold_images(st.session_state.team)
        if images:
            for img in images:
                iid, uploader, data, ts, team = img
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
                team_to_clear = st.selectbox("Select Team:", ["All Teams"] + get_all_teams())
                st.warning("This will permanently delete ALL requests and their comments!")
                if st.form_submit_button("Clear All Requests"):
                    if team_to_clear == "All Teams":
                        if clear_all_requests():
                            st.success("All requests deleted!")
                            st.rerun()
                    else:
                        if clear_all_requests(team_to_clear):
                            st.success(f"All requests for {team_to_clear} deleted!")
                            st.rerun()

        with st.expander("❌ Clear All Mistakes"):
            with st.form("clear_mistakes_form"):
                team_to_clear = st.selectbox("Select Team:", ["All Teams"] + get_all_teams())
                st.warning("This will permanently delete ALL mistakes!")
                if st.form_submit_button("Clear All Mistakes"):
                    if team_to_clear == "All Teams":
                        if clear_all_mistakes():
                            st.success("All mistakes deleted!")
                            st.rerun()
                    else:
                        if clear_all_mistakes(team_to_clear):
                            st.success(f"All mistakes for {team_to_clear} deleted!")
                            st.rerun()

        with st.expander("❌ Clear All Chat Messages"):
            with st.form("clear_chat_form"):
                team_to_clear = st.selectbox("Select Team:", ["All Teams"] + get_all_teams())
                skillset_to_clear = st.selectbox("Select Skillset:", ["All Skillsets"] + get_skillsets())
                st.warning("This will permanently delete ALL chat messages!")
                if st.form_submit_button("Clear All Chat"):
                    if team_to_clear == "All Teams" and skillset_to_clear == "All Skillsets":
                        if clear_all_group_messages():
                            st.success("All chat messages deleted!")
                            st.rerun()
                    elif team_to_clear == "All Teams":
                        if clear_all_group_messages(skillset=skillset_to_clear):
                            st.success(f"All {skillset_to_clear} chat messages deleted!")
                            st.rerun()
                    elif skillset_to_clear == "All Skillsets":
                        if clear_all_group_messages(team=team_to_clear):
                            st.success(f"All chat messages for {team_to_clear} deleted!")
                            st.rerun()
                    else:
                        if clear_all_group_messages(team_to_clear, skillset_to_clear):
                            st.success(f"All {skillset_to_clear} chat messages for {team_to_clear} deleted!")
                            st.rerun()

        with st.expander("❌ Clear All HOLD Images"):
            with st.form("clear_hold_form"):
                team_to_clear = st.selectbox("Select Team:", ["All Teams"] + get_all_teams())
                st.warning("This will permanently delete ALL HOLD images!")
                if st.form_submit_button("Clear All HOLD Images"):
                    if team_to_clear == "All Teams":
                        if clear_hold_images():
                            st.success("All HOLD images deleted!")
                            st.rerun()
                    else:
                        if clear_hold_images(team_to_clear):
                            st.success(f"All HOLD images for {team_to_clear} deleted!")
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
                role = st.selectbox("Role", ["agent", "admin", "team_leader"])
                team = st.selectbox("Team", ["None"] + get_all_teams())
                skillset = st.selectbox("Skillset", ["None"] + get_skillsets())
                if st.form_submit_button("Add User"):
                    if user and pwd:
                        team = None if team == "None" else team
                        skillset = None if skillset == "None" else skillset
                        add_user(user, pwd, role, team, skillset)
                        st.rerun()
        
        st.subheader("Existing Users")
        users = get_all_users()
        for uid, uname, role, team in users:
            cols = st.columns([3, 1, 1, 1])
            cols[0].write(uname)
            cols[1].write(role.capitalize())
            cols[2].write(team or "N/A")
            if cols[3].button("Delete", key=f"del_{uid}") and not is_killswitch_enabled():
                delete_user(uid)
                st.rerun()

if __name__ == "__main__":
    inject_custom_css()
    st.write("Request Management System")
