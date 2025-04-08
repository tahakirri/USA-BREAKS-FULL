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
            "active_templates": [],
            "template_states": {
                "default": "standby"  # Changed to standby by default
            }
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(default_settings, f)
    
    # Default templates if not exists (empty template)
    if not os.path.exists(TEMPLATES_FILE):
        default_templates = {
            "default": {
                "description": "Default template (empty - edit to create breaks)",
                "shifts": {
                    "2pm": {},
                    "6pm": {}
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
            if "active_templates" not in settings:
                settings["active_templates"] = []
            if "template_states" not in settings:
                settings["template_states"] = {"default": "standby"}
            return settings
    except (FileNotFoundError, json.JSONDecodeError):
        # If settings file is corrupted, recreate it
        default_settings = {
            "max_per_slot": 3,
            "current_template": "default",
            "active_templates": [],
            "template_states": {
                "default": "standby"
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

# Check if a template is active
def is_template_active(template_name):
    settings = load_settings()
    return template_name in settings["active_templates"]

# Check if a break type is active
def is_break_active(template_name, shift, break_type):
    settings = load_settings()
    templates = load_templates()
    
    # First check if the template is active
    if not is_template_active(template_name):
        return False
        
    # Then check if the break exists in the template
    if template_name not in templates:
        return False
    if shift not in templates[template_name]["shifts"]:
        return False
    if break_type not in templates[template_name]["shifts"][shift]:
        return False
        
    return True

# Add a booking
def add_booking(agent_id, template_name, shift, break_type, slot, date):
    if not is_break_active(template_name, shift, break_type):
        return False
        
    bookings = load_bookings()
    
    # Create date key if not exists
    if date not in bookings:
        bookings[date] = {}
    
    # Create template key if not exists
    if template_name not in bookings[date]:
        bookings[date][template_name] = {}
    
    # Create shift key if not exists
    if shift not in bookings[date][template_name]:
        bookings[date][template_name][shift] = {}
    
    # Create break type key if not exists
    if break_type not in bookings[date][template_name][shift]:
        bookings[date][template_name][shift][break_type] = {}
    
    # Create slot key if not exists
    if slot not in bookings[date][template_name][shift][break_type]:
        bookings[date][template_name][shift][break_type][slot] = []
    
    # Add booking if not already booked
    if agent_id not in bookings[date][template_name][shift][break_type][slot]:
        bookings[date][template_name][shift][break_type][slot].append(agent_id)
        save_bookings(bookings)
        return True
    
    return False

# Remove a booking
def remove_booking(agent_id, template_name, shift, break_type, slot, date):
    bookings = load_bookings()
    
    # Check if booking exists
    if (date in bookings and template_name in bookings[date] and 
        shift in bookings[date][template_name] and 
        break_type in bookings[date][template_name][shift] and 
        slot in bookings[date][template_name][shift][break_type] and 
        agent_id in bookings[date][template_name][shift][break_type][slot]):
        
        # Remove booking
        bookings[date][template_name][shift][break_type][slot].remove(agent_id)
        
        # Clean up empty structures
        if not bookings[date][template_name][shift][break_type][slot]:
            del bookings[date][template_name][shift][break_type][slot]
        if not bookings[date][template_name][shift][break_type]:
            del bookings[date][template_name][shift][break_type]
        if not bookings[date][template_name][shift]:
            del bookings[date][template_name][shift]
        if not bookings[date][template_name]:
            del bookings[date][template_name]
        if not bookings[date]:
            del bookings[date]
        
        save_bookings(bookings)
        return True
    
    return False

# Count bookings for a slot
def count_bookings(template_name, shift, break_type, slot, date):
    bookings = load_bookings()
    
    try:
        return len(bookings[date][template_name][shift][break_type][slot])
    except KeyError:
        return 0

# Get all agent bookings for a date
def get_agent_bookings(agent_id, date):
    bookings = load_bookings()
    agent_bookings = {}
    
    if date in bookings:
        for template_name in bookings[date]:
            agent_bookings[template_name] = {"2pm": {}, "6pm": {}}
            for shift in bookings[date][template_name]:
                for break_type in bookings[date][template_name][shift]:
                    for slot in bookings[date][template_name][shift][break_type]:
                        if agent_id in bookings[date][template_name][shift][break_type][slot]:
                            if break_type not in agent_bookings[template_name][shift]:
                                agent_bookings[template_name][shift][break_type] = []
                            agent_bookings[template_name][shift][break_type].append(slot)
    
    return agent_bookings

# Check if an agent already has a booking for a break type on a date
def has_break_booking(agent_id, template_name, shift, break_type, date):
    agent_bookings = get_agent_bookings(agent_id, date)
    return (template_name in agent_bookings and 
            shift in agent_bookings[template_name] and 
            break_type in agent_bookings[template_name][shift])

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
    
    # Get settings and templates
    settings = load_settings()
    templates = load_templates()
    
    # Get all active templates
    active_templates = settings.get("active_templates", [])
    if not active_templates:
        st.warning("No active break schedules available. Please check back later.")
        return
    
    max_per_slot = settings["max_per_slot"]
    
    # Create tabs for each active template
    template_tabs = st.tabs([f"{name} - {templates[name].get('description', '')}" for name in active_templates])
    
    for i, template_name in enumerate(active_templates):
        with template_tabs[i]:
            st.subheader(f"{template_name} Break Schedule")
            
            # Get the template data
            template = templates[template_name]
            
            # Create tabs for the two shifts
            tab1, tab2 = st.tabs(["2:00 PM Shift", "6:00 PM Shift"])
            
            # 2 PM Shift
            with tab1:
                if not template["shifts"]["2pm"]:
                    st.info("No breaks configured for 2pm shift")
                else:
                    st.subheader("2:00 PM Shift")
                    cols = st.columns(len(template["shifts"]["2pm"]))
                    
                    for j, (break_type, break_data) in enumerate(template["shifts"]["2pm"].items()):
                        with cols[j]:
                            st.markdown(f"### {break_type.replace('_', ' ').title()}")
                            
                            # Check if agent has booking for this break type
                            has_booking = has_break_booking(agent_id, template_name, "2pm", break_type, date_str)
                            
                            if has_booking:
                                booked_slots = agent_bookings[template_name]["2pm"][break_type]
                                st.success(f"Booked: {', '.join(booked_slots)}")
                                if st.button(f"Cancel {break_type.replace('_', ' ').title()} Booking (2PM)", 
                                           key=f"cancel_{break_type}_2pm_{template_name}"):
                                    for slot in booked_slots:
                                        remove_booking(agent_id, template_name, "2pm", break_type, slot, date_str)
                                    st.rerun()
                            else:
                                available_slots = []
                                for slot in break_data["slots"]:
                                    count = count_bookings(template_name, "2pm", break_type, slot, date_str)
                                    if count < max_per_slot:
                                        available_slots.append(f"{slot} ({count}/{max_per_slot})")
                                
                                if available_slots:
                                    selected_slot = st.selectbox(f"Select {break_type.replace('_', ' ').title()} Time (2PM)", 
                                                               available_slots, 
                                                               key=f"select_{break_type}_2pm_{template_name}")
                                    if st.button(f"Book {break_type.replace('_', ' ').title()} (2PM)", 
                                               key=f"book_{break_type}_2pm_{template_name}"):
                                        slot = selected_slot.split(" ")[0]
                                        success = add_booking(agent_id, template_name, "2pm", break_type, slot, date_str)
                                        if success:
                                            st.success(f"Booked {break_type.replace('_', ' ')} at {slot}")
                                            st.rerun()
                                        else:
                                            st.error("Booking failed. Please try again.")
                                else:
                                    st.info("No available slots")
            
            # 6 PM Shift
            with tab2:
                if not template["shifts"]["6pm"]:
                    st.info("No breaks configured for 6pm shift")
                else:
                    st.subheader("6:00 PM Shift")
                    cols = st.columns(len(template["shifts"]["6pm"]))
                    
                    for j, (break_type, break_data) in enumerate(template["shifts"]["6pm"].items()):
                        with cols[j]:
                            st.markdown(f"### {break_type.replace('_', ' ').title()}")
                            
                            # Check if agent has booking for this break type
                            has_booking = has_break_booking(agent_id, template_name, "6pm", break_type, date_str)
                            
                            if has_booking:
                                booked_slots = agent_bookings[template_name]["6pm"][break_type]
                                st.success(f"Booked: {', '.join(booked_slots)}")
                                if st.button(f"Cancel {break_type.replace('_', ' ').title()} Booking (6PM)", 
                                           key=f"cancel_{break_type}_6pm_{template_name}"):
                                    for slot in booked_slots:
                                        remove_booking(agent_id, template_name, "6pm", break_type, slot, date_str)
                                    st.rerun()
                            else:
                                available_slots = []
                                for slot in break_data["slots"]:
                                    count = count_bookings(template_name, "6pm", break_type, slot, date_str)
                                    if count < max_per_slot:
                                        available_slots.append(f"{slot} ({count}/{max_per_slot})")
                                
                                if available_slots:
                                    selected_slot = st.selectbox(f"Select {break_type.replace('_', ' ').title()} Time (6PM)", 
                                                               available_slots, 
                                                               key=f"select_{break_type}_6pm_{template_name}")
                                    if st.button(f"Book {break_type.replace('_', ' ').title()} (6PM)", 
                                               key=f"book_{break_type}_6pm_{template_name}"):
                                        slot = selected_slot.split(" ")[0]
                                        success = add_booking(agent_id, template_name, "6pm", break_type, slot, date_str)
                                        if success:
                                            st.success(f"Booked {break_type.replace('_', ' ')} at {slot}")
                                            st.rerun()
                                        else:
                                            st.error("Booking failed. Please try again.")
                                else:
                                    st.info("No available slots")

# Admin Interface
def admin_interface():
    st.header("Break Booking System - Admin View")
    
    # Load settings and templates
    settings = load_settings()
    templates = load_templates()
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["View Bookings", "Manage Slots", "Settings", "Templates", "Template Activation"])
    
    # Tab 1: View Bookings
    with tab1:
        st.subheader("View All Bookings")
        
        # Date selector
        date = st.date_input("Select Date to View", key="view_date_selector")
        date_str = date.strftime("%Y-%m-%d")
        
        # Load bookings
        bookings = load_bookings()
        
        if date_str in bookings:
            for template_name in bookings[date_str]:
                st.markdown(f"### Template: {template_name}")
                
                # 2 PM Shift
                st.markdown("#### 2:00 PM Shift")
                
                if "2pm" in bookings[date_str][template_name]:
                    cols = st.columns(len(bookings[date_str][template_name]["2pm"]))
                    
                    for i, (break_type, slots) in enumerate(bookings[date_str][template_name]["2pm"].items()):
                        with cols[i]:
                            st.markdown(f"##### {break_type.replace('_', ' ').title()}")
                            break_data = []
                            for slot, agents in slots.items():
                                for agent in agents:
                                    break_data.append({
                                        "Template": template_name,
                                        "Time": slot,
                                        "Agent ID": agent,
                                        "Break Type": break_type.replace('_', ' ').title(),
                                        "Shift": "2pm"
                                    })
                            
                            if break_data:
                                df = pd.DataFrame(break_data)
                                st.dataframe(df)
                            else:
                                st.info("No bookings")
                else:
                    st.info("No bookings for 2pm shift")
                
                # 6 PM Shift
                st.markdown("#### 6:00 PM Shift")
                
                if "6pm" in bookings[date_str][template_name]:
                    cols = st.columns(len(bookings[date_str][template_name]["6pm"]))
                    
                    for i, (break_type, slots) in enumerate(bookings[date_str][template_name]["6pm"].items()):
                        with cols[i]:
                            st.markdown(f"##### {break_type.replace('_', ' ').title()}")
                            break_data = []
                            for slot, agents in slots.items():
                                for agent in agents:
                                    break_data.append({
                                        "Template": template_name,
                                        "Time": slot,
                                        "Agent ID": agent,
                                        "Break Type": break_type.replace('_', ' ').title(),
                                        "Shift": "6pm"
                                    })
                            
                            if break_data:
                                df = pd.DataFrame(break_data)
                                st.dataframe(df)
                            else:
                                st.info("No bookings")
                else:
                    st.info("No bookings for 6pm shift")
        else:
            st.info(f"No bookings found for {date_str}")
    
    # Tab 2: Manage Slots
    with tab2:
        st.subheader("Manage Break Slots")
        
        # Template selector
        template_names = list(templates.keys())
        selected_template = st.selectbox("Select Template", template_names, key="manage_slots_template")
        
        if selected_template in templates:
            template = templates[selected_template]
            
            shift_option = st.selectbox("Select Shift", ["2pm", "6pm"], key="manage_slots_shift")
            break_type_option = st.text_input("Break Type Name (e.g., 'early_tea', 'lunch')", key="manage_slots_break_type")
            
            # Check if break type exists
            if break_type_option in template["shifts"][shift_option]:
                # Display current slots
                current_slots = template["shifts"][shift_option][break_type_option]["slots"]
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
                        templates[selected_template]["shifts"][shift_option][break_type_option]["slots"] = slots_list
                        save_templates(templates)
                        st.success(f"Slots updated for {shift_option} shift {break_type_option}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating slots: {str(e)}")
            
            # Add new break type
            st.markdown("### Add New Break Type")
            new_break_type = st.text_input("New Break Type Name", key="new_break_type")
            new_break_slots = st.text_area("Slots (comma-separated times)", key="new_break_slots")
            
            if st.button("Add Break Type", key="add_break_type"):
                if new_break_type and new_break_slots:
                    try:
                        # Parse and validate slots
                        slots_list = [slot.strip() for slot in new_break_slots.split(",")]
                        
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
                        
                        # Add to template
                        if new_break_type not in templates[selected_template]["shifts"][shift_option]:
                            templates[selected_template]["shifts"][shift_option][new_break_type] = {
                                "slots": slots_list
                            }
                            save_templates(templates)
                            st.success(f"Added new break type '{new_break_type}'!")
                            st.rerun()
                        else:
                            st.error("Break type already exists!")
                    except Exception as e:
                        st.error(f"Error adding break type: {str(e)}")
                else:
                    st.error("Please enter both break type name and slots")
    
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
        
        st.markdown(f"**Current Template:** {current_template_name}")
        
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
    
    # Tab 5: Template Activation
    with tab5:
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
                        
                        save_settings(settings)
                        st.success(f"Template '{template_name}' state updated to {new_state}!")
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
