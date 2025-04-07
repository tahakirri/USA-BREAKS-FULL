import streamlit as st
from datetime import datetime
import pandas as pd
import json
import os

# Default break templates
DEFAULT_TEMPLATES = {
    "2:00 PM Shift": {
        "lunch": {
            "slots": {"18:30": 5, "19:00": 5, "19:30": 5, "20:00": 5, "20:30": 5},
            "duration": 30,
            "max_bookings_per_agent": None
        },
        "tea_break_early": {
            "slots": {"15:00": 3, "15:15": 3, "15:30": 3, "15:45": 3, "16:00": 3, "16:15": 3, "16:30": 3},
            "duration": 15,
            "max_bookings_per_agent": 1
        },
        "tea_break_late": {
            "slots": {"20:45": 3, "21:00": 3, "21:15": 3, "21:30": 3},
            "duration": 15,
            "max_bookings_per_agent": 1
        },
        "last_hour": {
            "start": "22:00",
            "end": "22:30",
            "bio_break_duration": 5
        }
    },
    "6:00 PM Shift": {
        "lunch": {
            "slots": {"21:00": 5, "21:30": 5, "22:00": 5, "22:30": 5},
            "duration": 30,
            "max_bookings_per_agent": None
        },
        "tea_break_early": {
            "slots": {"19:00": 3, "19:15": 3, "19:30": 3, "19:45": 3, "20:00": 3, "20:15": 3, "20:30": 3, "20:45": 3},
            "duration": 15,
            "max_bookings_per_agent": 1
        },
        "tea_break_late": {
            "slots": {"00:00": 3, "00:15": 3, "00:30": 3, "00:45": 3, "01:00": 3, "01:15": 3, "01:30": 3},
            "duration": 15,
            "max_bookings_per_agent": 1
        },
        "last_hour": {
            "start": "02:00",
            "end": "02:30",
            "bio_break_duration": 5
        }
    }
}

# Admin credentials
ADMIN_CREDENTIALS = {
    "admin": "admin123"
}

# File paths
TEMPLATES_FILE = "break_templates.json"
BOOKINGS_FILE = "bookings.json"

def initialize_files():
    """Initialize data files if they don't exist"""
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(DEFAULT_TEMPLATES, f)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            json.dump({}, f)

def load_templates():
    """Load templates from file"""
    try:
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_files()
        return DEFAULT_TEMPLATES

def load_bookings():
    """Load bookings from file"""
    try:
        with open(BOOKINGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_templates(templates):
    """Save templates to file"""
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f)

def save_bookings(bookings):
    """Save bookings to file"""
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(bookings, f)

def init_session_state():
    """Initialize session state"""
    if 'initialized' not in st.session_state:
        st.session_state.templates = load_templates()
        st.session_state.bookings = load_bookings()
        st.session_state.agent_id = None
        st.session_state.admin_mode = False
        st.session_state.initialized = True

def get_available_slots(shift, break_type):
    """Get available slots with capacity info"""
    if shift not in st.session_state.templates:
        return []
    
    break_data = st.session_state.templates[shift].get(break_type, {})
    slots = break_data.get("slots", {})
    
    available_slots = []
    for slot_time, slot_capacity in slots.items():
        current_bookings = len([b for b in st.session_state.bookings.get(shift, {}).get(break_type, []) 
                             if b.get("slot") == slot_time])
        available = slot_capacity is None or current_bookings < slot_capacity
        available_slots.append({
            "time": slot_time,
            "capacity": slot_capacity,
            "available": available,
            "booked": current_bookings
        })
    return available_slots

def admin_interface():
    """Admin dashboard interface"""
    st.title("Admin Dashboard")
    
    # Template management
    st.header("Break Templates Management")
    
    # Select template to edit
    template_names = list(st.session_state.templates.keys())
    selected_template = st.selectbox("Select template to edit:", template_names)
    
    if selected_template:
        template = st.session_state.templates[selected_template]
        
        # Edit template details
        with st.expander("Edit Template Details", expanded=True):
            new_name = st.text_input("Template Name:", value=selected_template)
            
            # Lunch settings
            st.subheader("Lunch Break Settings")
            lunch_slots_str = st.text_area("Lunch Slots (format: 'time:capacity, time:capacity'):", 
                                      value=", ".join([f"{k}:{v}" for k, v in template["lunch"]["slots"].items()]))
            lunch_duration = st.number_input("Lunch Duration (minutes):", 
                                          value=template["lunch"]["duration"], min_value=1)
            lunch_max_per_agent = st.number_input("Max Lunch Bookings per Agent (0 for unlimited):", 
                                               value=template["lunch"]["max_bookings_per_agent"] or 0)
            
            # Early Tea settings
            st.subheader("Early Tea Break Settings")
            tea_early_slots_str = st.text_area("Early Tea Slots (format: 'time:capacity, time:capacity'):", 
                                            value=", ".join([f"{k}:{v}" for k, v in template["tea_break_early"]["slots"].items()]))
            tea_early_duration = st.number_input("Early Tea Duration (minutes):", 
                                              value=template["tea_break_early"]["duration"], min_value=1)
            tea_early_max_per_agent = st.number_input("Max Early Tea Bookings per Agent (0 for unlimited):", 
                                                   value=template["tea_break_early"]["max_bookings_per_agent"] or 0)
            
            # Late Tea settings
            st.subheader("Late Tea Break Settings")
            tea_late_slots_str = st.text_area("Late Tea Slots (format: 'time:capacity, time:capacity'):", 
                                           value=", ".join([f"{k}:{v}" for k, v in template["tea_break_late"]["slots"].items()]))
            tea_late_duration = st.number_input("Late Tea Duration (minutes):", 
                                             value=template["tea_break_late"]["duration"], min_value=1)
            tea_late_max_per_agent = st.number_input("Max Late Tea Bookings per Agent (0 for unlimited):", 
                                                  value=template["tea_break_late"]["max_bookings_per_agent"] or 0)
            
            # Last hour settings
            st.subheader("Last Hour Settings")
            last_hour_start = st.text_input("Last Hour Start Time:", value=template["last_hour"]["start"])
            last_hour_end = st.text_input("Last Hour End Time:", value=template["last_hour"]["end"])
            bio_duration = st.number_input("Bio Break Duration in Last Hour (minutes):", 
                                        value=template["last_hour"]["bio_break_duration"], min_value=1)
            
            if st.button("Update Template"):
                try:
                    # Process slots
                    def process_slots(slots_str):
                        slots = {}
                        for item in slots_str.split(","):
                            item = item.strip()
                            if ":" in item:
                                time, capacity = item.split(":")
                                slots[time.strip()] = int(capacity.strip()) if capacity.strip() else None
                            else:
                                slots[item] = None
                        return slots
                    
                    template["lunch"]["slots"] = process_slots(lunch_slots_str)
                    template["lunch"]["duration"] = lunch_duration
                    template["lunch"]["max_bookings_per_agent"] = lunch_max_per_agent if lunch_max_per_agent > 0 else None
                    
                    template["tea_break_early"]["slots"] = process_slots(tea_early_slots_str)
                    template["tea_break_early"]["duration"] = tea_early_duration
                    template["tea_break_early"]["max_bookings_per_agent"] = tea_early_max_per_agent if tea_early_max_per_agent > 0 else None
                    
                    template["tea_break_late"]["slots"] = process_slots(tea_late_slots_str)
                    template["tea_break_late"]["duration"] = tea_late_duration
                    template["tea_break_late"]["max_bookings_per_agent"] = tea_late_max_per_agent if tea_late_max_per_agent > 0 else None
                    
                    template["last_hour"]["start"] = last_hour_start
                    template["last_hour"]["end"] = last_hour_end
                    template["last_hour"]["bio_break_duration"] = bio_duration
                    
                    # Handle name change
                    if new_name != selected_template:
                        st.session_state.templates[new_name] = st.session_state.templates.pop(selected_template)
                    
                    save_templates(st.session_state.templates)
                    st.success("Template updated successfully!")
                except Exception as e:
                    st.error(f"Error: {str(e)}. Please check your input format.")

def agent_interface():
    """Agent booking interface"""
    st.title("Agent Break Booking System")
    
    # Shift selection
    shift_names = list(st.session_state.templates.keys())
    shift = st.radio("Select your shift:", shift_names, horizontal=True)
    
    st.header(f"Book Breaks for {shift}")
    
    # Break booking section
    with st.expander("Book Your Breaks", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Lunch Break")
            lunch_slots = get_available_slots(shift, "lunch")
            if not lunch_slots:
                st.warning("No lunch slots available")
            else:
                lunch_options = [f"{slot['time']} ({slot['booked']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                                for slot in lunch_slots]
                selected_lunch = st.selectbox("Select lunch time:", lunch_options, key="lunch_select")
                lunch_time = selected_lunch.split(" ")[0]
                if st.button("Book Lunch Break", key="lunch_btn"):
                    book_break(shift, "lunch", lunch_time)
        
        with col2:
            st.subheader("Early Tea Break")
            tea_early_slots = get_available_slots(shift, "tea_break_early")
            if not tea_early_slots:
                st.warning("No early tea slots available")
            else:
                tea_early_options = [f"{slot['time']} ({slot['booked']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                                     for slot in tea_early_slots]
                selected_tea_early = st.selectbox("Select early tea time:", tea_early_options, key="tea_early_select")
                tea_early_time = selected_tea_early.split(" ")[0]
                if st.button("Book Early Tea Break", key="tea_early_btn"):
                    book_break(shift, "tea_break_early", tea_early_time)
        
        with col3:
            st.subheader("Late Tea Break")
            tea_late_slots = get_available_slots(shift, "tea_break_late")
            if not tea_late_slots:
                st.warning("No late tea slots available")
            else:
                tea_late_options = [f"{slot['time']} ({slot['booked']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                                    for slot in tea_late_slots]
                selected_tea_late = st.selectbox("Select late tea time:", tea_late_options, key="tea_late_select")
                tea_late_time = selected_tea_late.split(" ")[0]
                if st.button("Book Late Tea Break", key="tea_late_btn"):
                    book_break(shift, "tea_break_late", tea_late_time)

def book_break(shift, break_type, slot_time):
    """Book a break slot"""
    if shift not in st.session_state.bookings:
        st.session_state.bookings[shift] = {"lunch": [], "tea_break_early": [], "tea_break_late": []}
    
    # Check if agent already booked this type of break
    agent_bookings = [b for b in st.session_state.bookings[shift][break_type] 
                     if b["agent"] == st.session_state.agent_id]
    max_per_agent = st.session_state.templates[shift][break_type].get("max_bookings_per_agent")
    
    if max_per_agent is not None and len(agent_bookings) >= max_per_agent:
        st.warning(f"You can only book {max_per_agent} {break_type.replace('_', ' ')} per shift!")
        return
    
    # Check slot capacity
    slot_capacity = st.session_state.templates[shift][break_type]["slots"].get(slot_time)
    if slot_capacity is not None:
        current_bookings = len([b for b in st.session_state.bookings[shift][break_type] 
                              if b["slot"] == slot_time])
        if current_bookings >= slot_capacity:
            st.warning(f"This slot is already full!")
            return
    
    # Add booking
    booking = {
        "agent": st.session_state.agent_id,
        "slot": slot_time,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.bookings[shift][break_type].append(booking)
    save_bookings(st.session_state.bookings)
    st.success(f"Booked {break_type.replace('_', ' ')} at {slot_time}!")

def login_page():
    """Login page for agents and admins"""
    st.title("Break Booking System Login")
    
    login_tab, admin_tab = st.tabs(["Agent Login", "Admin Login"])
    
    with login_tab:
        agent_id = st.text_input("Enter your Agent ID:", key="agent_input")
        if st.button("Agent Login") and agent_id:
            st.session_state.agent_id = agent_id
    
    with admin_tab:
        admin_user = st.text_input("Admin Username:", key="admin_user")
        admin_pass = st.text_input("Admin Password:", type="password", key="admin_pass")
        if st.button("Admin Login") and admin_user and admin_pass:
            if admin_user in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[admin_user] == admin_pass:
                st.session_state.admin_mode = True
            else:
                st.error("Invalid admin credentials")

def main():
    """Main application function"""
    initialize_files()
    init_session_state()
    
    # Show login page if not logged in
    if not st.session_state.agent_id and not st.session_state.admin_mode:
        login_page()
        return
    
    # Logout button
    if st.button("Logout"):
        st.session_state.agent_id = None
        st.session_state.admin_mode = False
        return
    
    # Show appropriate interface
    if st.session_state.admin_mode:
        admin_interface()
    else:
        agent_interface()

if __name__ == "__main__":
    main()
