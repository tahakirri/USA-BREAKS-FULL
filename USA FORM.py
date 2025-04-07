import streamlit as st
from datetime import datetime
import pandas as pd
import json
import os

# Default break templates with proper structure
DEFAULT_TEMPLATES = {
    "2:00 PM Shift": {
        "lunch": {
            "slots": {"18:30": 5, "19:00": 5, "19:30": 5, "20:00": 5, "20:30": 5},
            "duration": 30,
            "max_bookings_per_slot": None
        },
        "tea_break_early": {
            "slots": {"15:00": 3, "15:15": 3, "15:30": 3, "15:45": 3, "16:00": 3, "16:15": 3, "16:30": 3},
            "duration": 15,
            "max_bookings_per_slot": None
        },
        "tea_break_late": {
            "slots": {"20:45": 3, "21:00": 3, "21:15": 3, "21:30": 3},
            "duration": 15,
            "max_bookings_per_slot": None
        },
        "last_hour": {
            "start": "22:00",
            "end": "22:30",
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

def initialize_default_files():
    """Initialize data files with default templates if they don't exist"""
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(DEFAULT_TEMPLATES, f)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            json.dump({}, f)

def load_data():
    """Load templates and bookings data"""
    try:
        with open(TEMPLATES_FILE, 'r') as f:
            templates = json.load(f)
        with open(BOOKINGS_FILE, 'r') as f:
            bookings = json.load(f)
        return templates, bookings
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_default_files()
        return DEFAULT_TEMPLATES, {}

def save_data(templates, bookings):
    """Save templates and bookings data"""
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f)
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(bookings, f)

def init_session_state():
    """Initialize session state"""
    if 'initialized' not in st.session_state:
        templates, bookings = load_data()
        st.session_state.templates = templates
        st.session_state.bookings = bookings
        st.session_state.agent_id = None
        st.session_state.admin_mode = False
        st.session_state.initialized = True

def get_slots_with_capacity(shift, break_type):
    """Get available slots with capacity information"""
    if shift not in st.session_state.templates:
        return []
    
    break_data = st.session_state.templates[shift].get(break_type, {})
    slots = break_data.get("slots", {})
    
    if not isinstance(slots, dict):
        # Convert old format to new format if needed
        slots = {slot: None for slot in slots} if isinstance(slots, list) else {}
        st.session_state.templates[shift][break_type]["slots"] = slots
        save_data(st.session_state.templates, st.session_state.bookings)
    
    available_slots = []
    for slot, capacity in slots.items():
        current_bookings = len([b for b in st.session_state.bookings.get(shift, {}).get(break_type, []) 
                          if b["slot"] == slot])
        available = capacity is None or current_bookings < capacity
        available_slots.append({
            "time": slot,
            "capacity": capacity,
            "available": available,
            "current": current_bookings
        })
    return available_slots

def admin_interface():
    """Admin dashboard for managing break templates"""
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
            lunch_slots_str = st.text_area("Lunch Slots (format: 'time:max_agents, time:max_agents'):", 
                                      value=", ".join([f"{k}:{v}" for k, v in template["lunch"]["slots"].items()]))
            lunch_duration = st.number_input("Lunch Duration (minutes):", 
                                           value=template["lunch"]["duration"], min_value=1)
            
            # Early Tea settings
            st.subheader("Early Tea Break Settings")
            tea_early_slots_str = st.text_area("Early Tea Slots (format: 'time:max_agents, time:max_agents'):", 
                                         value=", ".join([f"{k}:{v}" for k, v in template["tea_break_early"]["slots"].items()]))
            tea_early_duration = st.number_input("Early Tea Duration (minutes):", 
                                               value=template["tea_break_early"]["duration"], min_value=1)
            
            # Late Tea settings
            st.subheader("Late Tea Break Settings")
            tea_late_slots_str = st.text_area("Late Tea Slots (format: 'time:max_agents, time:max_agents'):", 
                                        value=", ".join([f"{k}:{v}" for k, v in template["tea_break_late"]["slots"].items()]))
            tea_late_duration = st.number_input("Late Tea Duration (minutes):", 
                                              value=template["tea_break_late"]["duration"], min_value=1)
            
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
                            if ":" in item:
                                time, max_agents = item.strip().split(":")
                                slots[time.strip()] = int(max_agents.strip())
                            else:
                                slots[item.strip()] = None  # Unlimited capacity
                        return slots
                    
                    template["lunch"]["slots"] = process_slots(lunch_slots_str)
                    template["lunch"]["duration"] = lunch_duration
                    
                    template["tea_break_early"]["slots"] = process_slots(tea_early_slots_str)
                    template["tea_break_early"]["duration"] = tea_early_duration
                    
                    template["tea_break_late"]["slots"] = process_slots(tea_late_slots_str)
                    template["tea_break_late"]["duration"] = tea_late_duration
                    
                    template["last_hour"]["start"] = last_hour_start
                    template["last_hour"]["end"] = last_hour_end
                    template["last_hour"]["bio_break_duration"] = bio_duration
                    
                    # Handle name change
                    if new_name != selected_template:
                        st.session_state.templates[new_name] = st.session_state.templates.pop(selected_template)
                    
                    save_data(st.session_state.templates, st.session_state.bookings)
                    st.success("Template updated successfully!")
                except Exception as e:
                    st.error(f"Error processing input: {str(e)}. Please use format 'time:max_agents, time:max_agents'")

def agent_interface():
    """Agent interface for booking breaks"""
    st.title("Agent Break Booking System")
    
    # Shift selection
    shift_names = list(st.session_state.templates.keys())
    if not shift_names:
        st.error("No shift templates available. Please contact admin.")
        return
    
    shift = st.radio("Select your shift:", shift_names, horizontal=True)
    
    st.header(f"Book Breaks for {shift}")
    
    # Break booking section
    with st.expander("Book Your Breaks", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Lunch Break")
            lunch_slots = get_slots_with_capacity(shift, "lunch")
            if not lunch_slots:
                st.warning("No lunch slots available")
            else:
                lunch_options = [f"{slot['time']} ({slot['current']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                               for slot in lunch_slots]
                selected_lunch = st.selectbox("Select lunch time:", lunch_options, key="lunch_select")
                lunch_time = selected_lunch.split(" ")[0]
                if st.button("Book Lunch Break", key="lunch_btn"):
                    book_break(shift, "lunch", lunch_time)
        
        with col2:
            st.subheader("Early Tea Break")
            tea_early_slots = get_slots_with_capacity(shift, "tea_break_early")
            if not tea_early_slots:
                st.warning("No early tea slots available")
            else:
                tea_early_options = [f"{slot['time']} ({slot['current']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                                    for slot in tea_early_slots]
                selected_tea_early = st.selectbox("Select early tea time:", tea_early_options, key="tea_early_select")
                tea_early_time = selected_tea_early.split(" ")[0]
                if st.button("Book Early Tea Break", key="tea_early_btn"):
                    book_break(shift, "tea_break_early", tea_early_time)
        
        with col3:
            st.subheader("Late Tea Break")
            tea_late_slots = get_slots_with_capacity(shift, "tea_break_late")
            if not tea_late_slots:
                st.warning("No late tea slots available")
            else:
                tea_late_options = [f"{slot['time']} ({slot['current']}/{slot['capacity'] if slot['capacity'] else '∞'})" 
                                  for slot in tea_late_slots]
                selected_tea_late = st.selectbox("Select late tea time:", tea_late_options, key="tea_late_select")
                tea_late_time = selected_tea_late.split(" ")[0]
                if st.button("Book Late Tea Break", key="tea_late_btn"):
                    book_break(shift, "tea_break_late", tea_late_time)

def book_break(shift, break_type, slot):
    """Book a break slot for an agent"""
    if shift not in st.session_state.bookings:
        st.session_state.bookings[shift] = {"lunch": [], "tea_break_early": [], "tea_break_late": []}
    
    # Check if agent already booked this type of break
    user_bookings = [b for b in st.session_state.bookings[shift][break_type] if b["agent"] == st.session_state.agent_id]
    max_bookings = st.session_state.templates[shift][break_type].get("max_bookings_per_slot")
    
    if max_bookings is not None and len(user_bookings) >= max_bookings:
        st.warning(f"You can only book {max_bookings} {break_type.replace('_', ' ')} per shift!")
        return
    
    # Check slot capacity
    slot_capacity = st.session_state.templates[shift][break_type]["slots"].get(slot)
    if slot_capacity is not None:
        current_bookings = len([b for b in st.session_state.bookings[shift][break_type] if b["slot"] == slot])
        if current_bookings >= slot_capacity:
            st.warning(f"This {break_type.replace('_', ' ')} slot at {slot} is already full!")
            return
    
    # Add the booking
    booking = {
        "agent": st.session_state.agent_id,
        "slot": slot,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.bookings[shift][break_type].append(booking)
    save_data(st.session_state.templates, st.session_state.bookings)
    st.success(f"Booked {break_type.replace('_', ' ')} at {slot}!")

def main():
    """Main application function"""
    init_session_state()
    
    # Login section
    if not st.session_state.agent_id and not st.session_state.admin_mode:
        st.title("Break Booking System Login")
        
        login_tab, admin_tab = st.tabs(["Agent Login", "Admin Login"])
        
        with login_tab:
            agent_id = st.text_input("Enter your Agent ID:", key="agent_input")
            if st.button("Agent Login") and agent_id:
                st.session_state.agent_id = agent_id
                st.experimental_rerun()
        
        with admin_tab:
            admin_user = st.text_input("Admin Username:", key="admin_user")
            admin_pass = st.text_input("Admin Password:", type="password", key="admin_pass")
            if st.button("Admin Login") and admin_user and admin_pass:
                if admin_user in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[admin_user] == admin_pass:
                    st.session_state.admin_mode = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid admin credentials")
        
        return
    
    # Logout button
    if st.button("Logout"):
        st.session_state.agent_id = None
        st.session_state.admin_mode = False
        st.experimental_rerun()
    
    # Show appropriate interface
    if st.session_state.admin_mode:
        admin_interface()
    else:
        agent_interface()

if __name__ == "__main__":
    main()
