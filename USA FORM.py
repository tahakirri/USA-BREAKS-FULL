import streamlit as st
import pandas as pd
from datetime import datetime, time
import json
import os
import hashlib

# File paths for storing data
BOOKINGS_FILE = "bookings.json"
SETTINGS_FILE = "settings.json"
TEMPLATES_FILE = "templates.json"

# Helper function to generate unique element IDs
def generate_element_id(*args):
    str_args = "|".join(str(arg) for arg in args)
    return hashlib.md5(str_args.encode()).hexdigest()

# Initialize app state
def initialize_app():
    # Default settings if not exists
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "max_per_slot": 3,
            "current_template": "default",
            "active_breaks": {
                "2pm": ["early_tea", "lunch", "late_tea"],
                "6pm": ["early_tea", "lunch", "late_tea"]
            }
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_settings, f)
    
    # Default templates if not exists
    if not os.path.exists(TEMPLATES_FILE):
        default_templates = {
            "default": {
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
        }
        with open(TEMPLATES_FILE, "w") as f:
            json.dump(default_templates, f)
    
    # Create empty bookings file if not exists
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "w") as f:
            json.dump({}, f)
    
    # Ensure current_template exists in templates
    settings = load_settings()
    templates = load_templates()
    if settings["current_template"] not in templates:
        settings["current_template"] = "default"
        save_settings(settings)

# Load data functions
def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
            # Ensure settings has required keys
            if "current_template" not in settings:
                settings["current_template"] = "default"
            if "max_per_slot" not in settings:
                settings["max_per_slot"] = 3
            if "active_breaks" not in settings:
                settings["active_breaks"] = {
                    "2pm": ["early_tea", "lunch", "late_tea"],
                    "6pm": ["early_tea", "lunch", "late_tea"]
                }
            return settings
    except (FileNotFoundError, json.JSONDecodeError):
        # If settings file is corrupted, recreate it
        default_settings = {
            "max_per_slot": 3,
            "current_template": "default",
            "active_breaks": {
                "2pm": ["early_tea", "lunch", "late_tea"],
                "6pm": ["early_tea", "lunch", "late_tea"]
            }
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_settings, f)
        return default_settings

def load_templates():
    try:
        with open(TEMPLATES_FILE, "r") as f:
            templates = json.load(f)
            # Ensure at least default template exists
            if "default" not in templates:
                initialize_app()  # Reinitialize if default template is missing
                templates = json.load(open(TEMPLATES_FILE, "r"))
            return templates
    except (FileNotFoundError, json.JSONDecodeError):
        # If templates file is corrupted, recreate it
        initialize_app()
        return json.load(open(TEMPLATES_FILE, "r"))

def load_bookings():
    try:
        with open(BOOKINGS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If bookings file is corrupted, recreate it
        with open(BOOKINGS_FILE, "w") as f:
            json.dump({}, f)
        return {}

# Save data functions
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def save_templates(templates):
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(templates, f)

def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f)

# Get current template data with error handling
def get_current_template():
    settings = load_settings()
    templates = load_templates()
    
    # If the current_template doesn't exist, fall back to "default"
    if settings["current_template"] not in templates:
        settings["current_template"] = "default"
        save_settings(settings)
    
    return templates[settings["current_template"]]

# Check if a break type is active
def is_break_active(shift, break_type):
    settings = load_settings()
    return break_type in settings["active_breaks"].get(shift, [])

# Add a booking
def add_booking(agent_id, shift, break_type, slot, date):
    if not is_break_active(shift, break_type):
        return False
        
    bookings = load_bookings()
    
    # Create date key if not exists
    if date not in bookings:
        bookings[date] = {}
    
    # Create shift key if not exists
    if shift not in bookings[date]:
        bookings[date][shift] = {}
    
    # Create break type key if not exists
    if break_type not in bookings[date][shift]:
        bookings[date][shift][break_type] = {}
    
    # Create slot key if not exists
    if slot not in bookings[date][shift][break_type]:
        bookings[date][shift][break_type][slot] = []
    
    # Add booking if not already booked
    if agent_id not in bookings[date][shift][break_type][slot]:
        bookings[date][shift][break_type][slot].append(agent_id)
        save_bookings(bookings)
        return True
    
    return False

# Remove a booking
def remove_booking(agent_id, shift, break_type, slot, date):
    bookings = load_bookings()
    
    # Check if booking exists
    if (date in bookings and shift in bookings[date] and 
        break_type in bookings[date][shift] and 
        slot in bookings[date][shift][break_type] and 
        agent_id in bookings[date][shift][break_type][slot]):
        
        # Remove booking
        bookings[date][shift][break_type][slot].remove(agent_id)
        
        # Clean up empty structures
        if not bookings[date][shift][break_type][slot]:
            del bookings[date][shift][break_type][slot]
        if not bookings[date][shift][break_type]:
            del bookings[date][shift][break_type]
        if not bookings[date][shift]:
            del bookings[date][shift]
        if not bookings[date]:
            del bookings[date]
        
        save_bookings(bookings)
        return True
    
    return False

# Count bookings for a slot
def count_bookings(shift, break_type, slot, date):
    bookings = load_bookings()
    
    try:
        return len(bookings[date][shift][break_type][slot])
    except KeyError:
        return 0

# Get all agent bookings for a date
def get_agent_bookings(agent_id, date):
    bookings = load_bookings()
    agent_bookings = {"2pm": {}, "6pm": {}}
    
    if date in bookings:
        for shift in bookings[date]:
            for break_type in bookings[date][shift]:
                for slot in bookings[date][shift][break_type]:
                    if agent_id in bookings[date][shift][break_type][slot]:
                        if break_type not in agent_bookings[shift]:
                            agent_bookings[shift][break_type] = []
                        agent_bookings[shift][break_type].append(slot)
    
    return agent_bookings

# Check if an agent already has a booking for a break type on a date
def has_break_booking(agent_id, shift, break_type, date):
    agent_bookings = get_agent_bookings(agent_id, date)
    return break_type in agent_bookings[shift]

# Clear all bookings
def clear_all_bookings():
    with open(BOOKINGS_FILE, "w") as f:
        json.dump({}, f)

# Agent Interface
def agent_interface():
    st.header("Break Booking System - Agent View")
    
    # Agent ID input
    agent_id = st.text_input("Enter your Agent ID", key="agent_id_input")
    
    # Date selector
    date = st.date_input("Select Date", key="agent_date_input")
    date_str = date.strftime("%Y-%m-%d")
    
    if not agent_id:
        st.warning("Please enter your Agent ID to proceed.")
        return
    
    # Load current bookings for this agent
    agent_bookings = get_agent_bookings(agent_id, date_str)
    
    # Get current template
    try:
        current_template = get_current_template()
        settings = load_settings()
    except Exception as e:
        st.error(f"Error loading break schedule: {str(e)}")
        st.stop()
    
    max_per_slot = settings["max_per_slot"]
    
    # Create tabs for the two shifts
    tab1, tab2 = st.tabs(["2:00 PM Shift", "6:00 PM Shift"])
    
    # 2 PM Shift
    with tab1:
        st.subheader("2:00 PM Shift")
        col1, col2, col3 = st.columns(3)
        
        # Early Tea Break
        if is_break_active("2pm", "early_tea"):
            with col1:
                st.markdown("### Early Tea Break")
                early_tea_booked = "early_tea" in agent_bookings["2pm"]
                
                if early_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['early_tea'])}")
                    if st.button("Cancel Early Tea Booking (2PM)", key="cancel_early_tea_2pm"):
                        for slot in agent_bookings["2pm"]["early_tea"]:
                            remove_booking(agent_id, "2pm", "early_tea", slot, date_str)
                        st.rerun()
                else:
                    early_tea_options = []
                    for slot in current_template["shifts"]["2pm"]["early_tea"]["slots"]:
                        count = count_bookings("2pm", "early_tea", slot, date_str)
                        if count < max_per_slot:
                            early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if early_tea_options:
                        selected_early_tea = st.selectbox("Select Early Tea Time (2PM)", early_tea_options, key="early_tea_2pm")
                        if st.button("Book Early Tea Break (2PM)", key="book_early_tea_2pm"):
                            slot = selected_early_tea.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "2pm", "early_tea", slot, date_str)
                            if success:
                                st.success(f"Booked Early Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Early Tea Break")
        
        # Lunch Break
        if is_break_active("2pm", "lunch"):
            with col2:
                st.markdown("### Lunch Break")
                lunch_booked = "lunch" in agent_bookings["2pm"]
                
                if lunch_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['lunch'])}")
                    if st.button("Cancel Lunch Booking (2PM)", key="cancel_lunch_2pm"):
                        for slot in agent_bookings["2pm"]["lunch"]:
                            remove_booking(agent_id, "2pm", "lunch", slot, date_str)
                        st.rerun()
                else:
                    lunch_options = []
                    for slot in current_template["shifts"]["2pm"]["lunch"]["slots"]:
                        count = count_bookings("2pm", "lunch", slot, date_str)
                        if count < max_per_slot:
                            lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if lunch_options:
                        selected_lunch = st.selectbox("Select Lunch Time (2PM)", lunch_options, key="lunch_2pm")
                        if st.button("Book Lunch Break (2PM)", key="book_lunch_2pm"):
                            slot = selected_lunch.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "2pm", "lunch", slot, date_str)
                            if success:
                                st.success(f"Booked Lunch Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Lunch Break")
        
        # Late Tea Break
        if is_break_active("2pm", "late_tea"):
            with col3:
                st.markdown("### Late Tea Break")
                late_tea_booked = "late_tea" in agent_bookings["2pm"]
                
                if late_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['2pm']['late_tea'])}")
                    if st.button("Cancel Late Tea Booking (2PM)", key="cancel_late_tea_2pm"):
                        for slot in agent_bookings["2pm"]["late_tea"]:
                            remove_booking(agent_id, "2pm", "late_tea", slot, date_str)
                        st.rerun()
                else:
                    late_tea_options = []
                    for slot in current_template["shifts"]["2pm"]["late_tea"]["slots"]:
                        count = count_bookings("2pm", "late_tea", slot, date_str)
                        if count < max_per_slot:
                            late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if late_tea_options:
                        selected_late_tea = st.selectbox("Select Late Tea Time (2PM)", late_tea_options, key="late_tea_2pm")
                        if st.button("Book Late Tea Break (2PM)", key="book_late_tea_2pm"):
                            slot = selected_late_tea.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "2pm", "late_tea", slot, date_str)
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
        if is_break_active("6pm", "early_tea"):
            with col1:
                st.markdown("### Early Tea Break")
                early_tea_booked = "early_tea" in agent_bookings["6pm"]
                
                if early_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['early_tea'])}")
                    if st.button("Cancel Early Tea Booking (6PM)", key="cancel_early_tea_6pm"):
                        for slot in agent_bookings["6pm"]["early_tea"]:
                            remove_booking(agent_id, "6pm", "early_tea", slot, date_str)
                        st.rerun()
                else:
                    early_tea_options = []
                    for slot in current_template["shifts"]["6pm"]["early_tea"]["slots"]:
                        count = count_bookings("6pm", "early_tea", slot, date_str)
                        if count < max_per_slot:
                            early_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if early_tea_options:
                        selected_early_tea = st.selectbox("Select Early Tea Time (6PM)", early_tea_options, key="early_tea_6pm")
                        if st.button("Book Early Tea Break (6PM)", key="book_early_tea_6pm"):
                            slot = selected_early_tea.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "6pm", "early_tea", slot, date_str)
                            if success:
                                st.success(f"Booked Early Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Early Tea Break")
        
        # Lunch Break
        if is_break_active("6pm", "lunch"):
            with col2:
                st.markdown("### Lunch Break")
                lunch_booked = "lunch" in agent_bookings["6pm"]
                
                if lunch_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['lunch'])}")
                    if st.button("Cancel Lunch Booking (6PM)", key="cancel_lunch_6pm"):
                        for slot in agent_bookings["6pm"]["lunch"]:
                            remove_booking(agent_id, "6pm", "lunch", slot, date_str)
                        st.rerun()
                else:
                    lunch_options = []
                    for slot in current_template["shifts"]["6pm"]["lunch"]["slots"]:
                        count = count_bookings("6pm", "lunch", slot, date_str)
                        if count < max_per_slot:
                            lunch_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if lunch_options:
                        selected_lunch = st.selectbox("Select Lunch Time (6PM)", lunch_options, key="lunch_6pm")
                        if st.button("Book Lunch Break (6PM)", key="book_lunch_6pm"):
                            slot = selected_lunch.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "6pm", "lunch", slot, date_str)
                            if success:
                                st.success(f"Booked Lunch Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Lunch Break")
        
        # Late Tea Break
        if is_break_active("6pm", "late_tea"):
            with col3:
                st.markdown("### Late Tea Break")
                late_tea_booked = "late_tea" in agent_bookings["6pm"]
                
                if late_tea_booked:
                    st.success(f"Booked: {', '.join(agent_bookings['6pm']['late_tea'])}")
                    if st.button("Cancel Late Tea Booking (6PM)", key="cancel_late_tea_6pm"):
                        for slot in agent_bookings["6pm"]["late_tea"]:
                            remove_booking(agent_id, "6pm", "late_tea", slot, date_str)
                        st.rerun()
                else:
                    late_tea_options = []
                    for slot in current_template["shifts"]["6pm"]["late_tea"]["slots"]:
                        count = count_bookings("6pm", "late_tea", slot, date_str)
                        if count < max_per_slot:
                            late_tea_options.append(f"{slot} ({count}/{max_per_slot})")
                    
                    if late_tea_options:
                        selected_late_tea = st.selectbox("Select Late Tea Time (6PM)", late_tea_options, key="late_tea_6pm")
                        if st.button("Book Late Tea Break (6PM)", key="book_late_tea_6pm"):
                            slot = selected_late_tea.split(" ")[0]  # Extract time from display format
                            success = add_booking(agent_id, "6pm", "late_tea", slot, date_str)
                            if success:
                                st.success(f"Booked Late Tea Break at {slot}")
                                st.rerun()
                            else:
                                st.error("Booking failed. Please try again.")
                    else:
                        st.info("No available slots for Late Tea Break")

# Admin Interface
def admin_interface():
    st.header("Break Booking System - Admin View")
    
    # Load settings and templates
    settings = load_settings()
    templates = load_templates()
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["View Bookings", "Manage Slots", "Settings", "Templates", "Active Breaks"])
    
    # Tab 1: View Bookings
    with tab1:
        st.subheader("View All Bookings")
        
        # Date selector
        date = st.date_input("Select Date to View", key="view_date_selector")
        date_str = date.strftime("%Y-%m-%d")
        
        # Load bookings
        bookings = load_bookings()
        
        # Get current template
        current_template = get_current_template()
        
        # Create dataframes for each shift and break type
        if date_str in bookings:
            # 2 PM Shift
            st.markdown("### 2:00 PM Shift")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### Early Tea Break")
                if "2pm" in bookings[date_str] and "early_tea" in bookings[date_str]["2pm"]:
                    early_tea_data = []
                    for slot in current_template["shifts"]["2pm"]["early_tea"]["slots"]:
                        if slot in bookings[date_str]["2pm"]["early_tea"]:
                            for agent in bookings[date_str]["2pm"]["early_tea"][slot]:
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
                if "2pm" in bookings[date_str] and "lunch" in bookings[date_str]["2pm"]:
                    lunch_data = []
                    for slot in current_template["shifts"]["2pm"]["lunch"]["slots"]:
                        if slot in bookings[date_str]["2pm"]["lunch"]:
                            for agent in bookings[date_str]["2pm"]["lunch"][slot]:
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
                if "2pm" in bookings[date_str] and "late_tea" in bookings[date_str]["2pm"]:
                    late_tea_data = []
                    for slot in current_template["shifts"]["2pm"]["late_tea"]["slots"]:
                        if slot in bookings[date_str]["2pm"]["late_tea"]:
                            for agent in bookings[date_str]["2pm"]["late_tea"][slot]:
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
                if "6pm" in bookings[date_str] and "early_tea" in bookings[date_str]["6pm"]:
                    early_tea_data = []
                    for slot in current_template["shifts"]["6pm"]["early_tea"]["slots"]:
                        if slot in bookings[date_str]["6pm"]["early_tea"]:
                            for agent in bookings[date_str]["6pm"]["early_tea"][slot]:
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
                if "6pm" in bookings[date_str] and "lunch" in bookings[date_str]["6pm"]:
                    lunch_data = []
                    for slot in current_template["shifts"]["6pm"]["lunch"]["slots"]:
                        if slot in bookings[date_str]["6pm"]["lunch"]:
                            for agent in bookings[date_str]["6pm"]["lunch"][slot]:
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
                if "6pm" in bookings[date_str] and "late_tea" in bookings[date_str]["6pm"]:
                    late_tea_data = []
                    for slot in current_template["shifts"]["6pm"]["late_tea"]["slots"]:
                        if slot in bookings[date_str]["6pm"]["late_tea"]:
                            for agent in bookings[date_str]["6pm"]["late_tea"][slot]:
                                late_tea_data.append({"Time": slot, "Agent ID": agent})
                    
                    if late_tea_data:
                        late_tea_df = pd.DataFrame(late_tea_data)
                        st.dataframe(late_tea_df)
                    else:
                        st.info("No bookings for Late Tea Break")
                else:
                    st.info("No bookings for Late Tea Break")
        else:
            st.info(f"No bookings found for {date_str}")
    
    # Tab 2: Manage Slots
    with tab2:
        st.subheader("Manage Break Slots")
        
        current_template = get_current_template()
        
        shift_option = st.selectbox("Select Shift", ["2pm", "6pm"], key="manage_slots_shift")
        break_type_option = st.selectbox("Select Break Type", ["early_tea", "lunch", "late_tea"], key="manage_slots_break_type")
        
        # Display current slots
        current_slots = current_template["shifts"][shift_option][break_type_option]["slots"]
        st.write("Current Slots:")
        st.write(", ".join(current_slots))
        
        # Edit slots
        new_slots = st.text_area("Edit Slots (comma-separated times in 24-hour format, e.g., 15:00, 15:15)", 
                                value=", ".join(current_slots), key="manage_slots_textarea")
        
        if st.button("Update Slots", key="update_slots_button"):
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
                templates = load_templates()
                current_template_name = settings["current_template"]
                templates[current_template_name]["shifts"][shift_option][break_type_option]["slots"] = slots_list
                save_templates(templates)
                st.success(f"Slots updated for {shift_option} shift {break_type_option}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating slots: {str(e)}")
    
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
            save_settings(settings)
            st.success(f"Maximum bookings per slot updated to {max_per_slot}!")
            st.rerun()
        
        # Bulk delete bookings
        st.markdown("### Delete Bookings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Delete All Bookings for a Date")
            delete_date = st.date_input("Select Date to Delete", key="delete_date_input")
            delete_date_str = delete_date.strftime("%Y-%m-%d")
            
            if st.button("Delete Date Bookings", key="delete_date_bookings", type="primary", use_container_width=True):
                bookings = load_bookings()
                if delete_date_str in bookings:
                    del bookings[delete_date_str]
                    save_bookings(bookings)
                    st.success(f"All bookings for {delete_date_str} have been deleted!")
                else:
                    st.info(f"No bookings found for {delete_date_str}")
        
        with col2:
            st.markdown("#### Clear All Bookings")
            st.warning("This will delete ALL bookings from the system!")
            if st.button("Clear All Bookings", key="clear_all_bookings", type="primary", use_container_width=True):
                clear_all_bookings()
                st.success("All bookings have been cleared!")
    
    # Tab 4: Templates
    with tab4:
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
        
        if st.button("Set as Active Template", key="set_active_template"):
            settings["current_template"] = selected_template
            save_settings(settings)
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
                    "shifts": json.loads(json.dumps(templates[copy_from]["shifts"]))  # Deep copy
                }
                templates[new_template_name] = new_template
                save_templates(templates)
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
                    templates[edit_template]["shifts"][shift_to_edit][break_to_edit]["slots"] = slots_list
                    save_templates(templates)
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
                    del templates[template_to_delete]
                    save_templates(templates)
                    st.success(f"Template '{template_to_delete}' deleted!")
                    st.rerun()
        else:
            st.info("Cannot delete the only remaining template")
    
    # Tab 5: Active Breaks
    with tab5:
        st.subheader("Manage Active Breaks")
        st.info("Select which breaks should be available for agents to book")
        
        # 2pm Shift
        st.markdown("### 2:00 PM Shift")
        early_tea_2pm = st.checkbox("Early Tea Break (2PM)", 
                                  value="early_tea" in settings["active_breaks"]["2pm"],
                                  key="early_tea_2pm_active")
        lunch_2pm = st.checkbox("Lunch Break (2PM)", 
                              value="lunch" in settings["active_breaks"]["2pm"],
                              key="lunch_2pm_active")
        late_tea_2pm = st.checkbox("Late Tea Break (2PM)", 
                                 value="late_tea" in settings["active_breaks"]["2pm"],
                                 key="late_tea_2pm_active")
        
        # 6pm Shift
        st.markdown("### 6:00 PM Shift")
        early_tea_6pm = st.checkbox("Early Tea Break (6PM)", 
                                  value="early_tea" in settings["active_breaks"]["6pm"],
                                  key="early_tea_6pm_active")
        lunch_6pm = st.checkbox("Lunch Break (6PM)", 
                              value="lunch" in settings["active_breaks"]["6pm"],
                              key="lunch_6pm_active")
        late_tea_6pm = st.checkbox("Late Tea Break (6PM)", 
                                 value="late_tea" in settings["active_breaks"]["6pm"],
                                 key="late_tea_6pm_active")
        
        if st.button("Save Active Breaks", key="save_active_breaks"):
            # Update active breaks for 2pm shift
            settings["active_breaks"]["2pm"] = []
            if early_tea_2pm:
                settings["active_breaks"]["2pm"].append("early_tea")
            if lunch_2pm:
                settings["active_breaks"]["2pm"].append("lunch")
            if late_tea_2pm:
                settings["active_breaks"]["2pm"].append("late_tea")
            
            # Update active breaks for 6pm shift
            settings["active_breaks"]["6pm"] = []
            if early_tea_6pm:
                settings["active_breaks"]["6pm"].append("early_tea")
            if lunch_6pm:
                settings["active_breaks"]["6pm"].append("lunch")
            if late_tea_6pm:
                settings["active_breaks"]["6pm"].append("late_tea")
            
            save_settings(settings)
            st.success("Active breaks configuration saved!")
            st.rerun()

# Main app
def main():
    st.set_page_config(page_title="Break Booking System", layout="wide")
    
    # Initialize app data
    initialize_app()
    
    # App title
    st.title("Break Booking System")
    
    # Create sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        app_mode = st.radio("Select Mode", ["Agent", "Admin"], key="app_mode_selector")
    
    # Show the appropriate interface
    if app_mode == "Agent":
        agent_interface()
    else:
        # Admin authentication (simple password for demo)
        admin_password = st.sidebar.text_input("Admin Password", type="password", key="admin_password")
        if admin_password == "admin123":  # In a real app, use a more secure authentication system
            admin_interface()
        else:
            st.warning("Please enter the admin password to access the admin panel.")

if __name__ == "__main__":
    main()
