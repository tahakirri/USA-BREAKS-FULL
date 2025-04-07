import streamlit as st
import pandas as pd
from datetime import datetime, time
import json
import os

# Constants
DATA_FILE = "break_data.json"
TEMPLATES_FILE = "break_templates.json"
SHIFT_1_START = time(15, 0)  # 3:00 PM
SHIFT_2_START = time(18, 0)  # 6:00 PM

# Initialize data structure with proper nested defaults
def init_data():
    return {
        "shifts": {
            "3pm_shift": initialize_shift("LM US ENG SUNDAY 3:00 PM shift", {
                "first_break": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
                "lunch": ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30"],
                "second_break": ["21:30", "21:45", "22:00", "22:15", "22:30"]
            }, "22:00-22:30"),
            "6pm_shift": initialize_shift("LM US ENG 6:00 PM shift", {
                "first_break": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"],
                "lunch": ["21:00", "21:30", "22:00", "22:30"],
                "second_break": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]
            }, "02:00-02:30")
        },
        "agents": {},
        "admin_password": "admin123"
    }

def initialize_shift(name, break_times, last_hour):
    return {
        "name": name,
        "break_types": {
            bt: {
                "name": " ".join(bt.split("_")).title(),
                "breaks": {time: {"slots": 5, "booked": []} for time in times}
            } for bt, times in break_times.items()
        },
        "last_hour": last_hour,
        "bio_only": True
    }

# Initialize templates
def init_templates():
    return {
        "default_template": {
            "first_break": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
            "lunch": ["19:00", "19:30", "20:00", "20:30", "21:00", "21:30"],
            "second_break": ["21:30", "21:45", "22:00", "22:15", "22:30"]
        },
        "late_shift_template": {
            "first_break": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"],
            "lunch": ["21:00", "21:30", "22:00", "22:30"],
            "second_break": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"]
        }
    }

# Load or initialize data with validation
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                # Validate and add missing keys
                for shift in data["shifts"].values():
                    shift.setdefault("last_hour", "00:00-00:00")
                    shift.setdefault("bio_only", True)
                    for bt in ["first_break", "lunch", "second_break"]:
                        shift["break_types"].setdefault(bt, {
                            "name": " ".join(bt.split("_")).title(),
                            "breaks": {}
                        })
                return data
        except:
            return init_data()
    return init_data()

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Load or initialize templates
def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, "r") as f:
            return json.load(f)
    return init_templates()

def save_templates(templates):
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(templates, f)

# Helper functions with validation
def get_current_shift():
    now = datetime.now().time()
    return "3pm_shift" if SHIFT_1_START <= now < SHIFT_2_START else "6pm_shift"

def is_admin():
    return st.session_state.get("is_admin", False)

def create_breaks_from_template(template, slots=5):
    return {time: {"slots": slots, "booked": []} for time in template}

# Admin panel with validation
def admin_panel(data):
    st.title("Admin Panel")
    templates = load_templates()
    
    if not is_admin():
        password = st.text_input("Enter Admin Password", type="password")
        if password == data.get("admin_password", ""):
            st.session_state["is_admin"] = True
            st.rerun()
        elif password:
            st.error("Incorrect password")
        return
    
    st.success("Logged in as Admin")
    
    # Password change section
    with st.expander("Change Admin Password"):
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        if st.button("Update Password") and new_pass == confirm_pass:
            data["admin_password"] = new_pass
            save_data(data)
            st.success("Password updated successfully")

    # Shift selection
    shift_key = st.selectbox("Select Shift", list(data["shifts"].keys()), 
                           format_func=lambda x: data["shifts"][x].get("name", "Unknown Shift"))
    
    # Template management
    with st.expander("Template Management"):
        # Template creation and application logic
        # ... [previous template code] ...

    # Break type selection
    break_type = st.selectbox("Select Break Type", 
                            ["first_break", "lunch", "second_break"],
                            format_func=lambda x: data["shifts"][shift_key]["break_types"][x].get("name", x))
    
    # Break editing with validation
    with st.expander("Edit Breaks"):
        if break_type not in data["shifts"][shift_key]["break_types"]:
            data["shifts"][shift_key]["break_types"][break_type] = {
                "name": " ".join(break_type.split("_")).title(),
                "breaks": {}
            }
        
        # Break editing interface
        # ... [previous break editing code] ...

    # Last hour rules editing
    with st.expander("Edit Last Hour Rules"):
        current_rules = data["shifts"][shift_key].get("last_hour", "00:00-00:00")
        last_hour = st.text_input("Last Hour (format: HH:MM-HH:MM)", value=current_rules)
        bio_only = st.checkbox("Bio Breaks Only in Last Hour", 
                             value=data["shifts"][shift_key].get("bio_only", True))
        if st.button("Update Last Hour Rules"):
            data["shifts"][shift_key]["last_hour"] = last_hour
            data["shifts"][shift_key]["bio_only"] = bio_only
            save_data(data)
            st.success("Rules updated")

# Agent interface with validation
def agent_booking(data, shift_key):
    shift = data["shifts"].get(shift_key, {})
    if not shift:
        st.error("Invalid shift selected")
        return
    
    st.title(shift.get("name", "Unknown Shift"))
    
    # Display rules safely
    last_hour = shift.get("last_hour", "00:00-00:00")
    end_time = last_hour.split('-')[1] if '-' in last_hour else "00:00"
    st.warning(f"""
    **RULES:**
    - NO BREAK IN THE LAST HOUR WILL BE AUTHORIZED
    - ONLY 5 MINUTES BIO IS AUTHORIZED IN THE LAST HOUR BETWEEN {last_hour}
    - NO BREAK AFTER {end_time} !!!
    - BREAKS SHOULD BE TAKEN AT THE NOTED TIME AND NEED TO BE CONFIRMED FROM RTA OR TEAM LEADERS
    """)
    
    agent_id = st.text_input("Enter Your Agent ID")
    if not agent_id:
        return
    
    # Initialize agent data structure
    data["agents"].setdefault(agent_id, {"bookings": {}})
    
    # Booking logic with validation
    # ... [previous booking code with added checks] ...

# Main app function
def main():
    st.set_page_config(page_title="Break Booking System", layout="wide")
    data = load_data()
    
    # Navigation
    if st.sidebar.button("Admin Login"):
        st.session_state["show_admin"] = True
    
    if st.session_state.get("show_admin", False):
        admin_panel(data)
        if st.sidebar.button("Back to Agent View"):
            st.session_state["show_admin"] = False
            st.rerun()
    else:
        current_shift = get_current_shift()
        shift_choice = st.sidebar.radio("Select Shift", 
                                       [data["shifts"]["3pm_shift"]["name"], 
                                       data["shifts"]["6pm_shift"]["name"]],
                                       index=0 if current_shift == "3pm_shift" else 1)
        
        shift_key = "3pm_shift" if shift_choice == data["shifts"]["3pm_shift"]["name"] else "6pm_shift"
        agent_booking(data, shift_key)

if __name__ == "__main__":
    main()
