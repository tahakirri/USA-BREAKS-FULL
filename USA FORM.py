import streamlit as st
from datetime import datetime
import pandas as pd
import json
import os

# Default break templates
DEFAULT_TEMPLATES = {
    "2:00 PM Shift": {
        "lunch": {
            "slots": ["18:30", "19:00", "19:30", "20:00", "20:30"],
            "duration": 30,
            "max_bookings": None
        },
        "tea_break_early": {
            "slots": ["15:00", "15:15", "15:30", "15:45", "16:00", "16:15", "16:30"],
            "duration": 15,
            "max_bookings": 1
        },
        "tea_break_late": {
            "slots": ["20:45", "21:00", "21:15", "21:30"],
            "duration": 15,
            "max_bookings": 1
        },
        "last_hour": {
            "start": "22:00",
            "end": "22:30",
            "bio_break_duration": 5
        }
    },
    "6:00 PM Shift": {
        "lunch": {
            "slots": ["21:00", "21:30", "22:00", "22:30"],
            "duration": 30,
            "max_bookings": None
        },
        "tea_break_early": {
            "slots": ["19:00", "19:15", "19:30", "19:45", "20:00", "20:15", "20:30", "20:45"],
            "duration": 15,
            "max_bookings": 1
        },
        "tea_break_late": {
            "slots": ["00:00", "00:15", "00:30", "00:45", "01:00", "01:15", "01:30"],
            "duration": 15,
            "max_bookings": 1
        },
        "last_hour": {
            "start": "02:00",
            "end": "02:30",
            "bio_break_duration": 5
        }
    }
}

# Admin credentials (in production, use proper authentication)
ADMIN_CREDENTIALS = {
    "admin": "admin123"
}

# File paths
TEMPLATES_FILE = "break_templates.json"
BOOKINGS_FILE = "bookings.json"

# Initialize data files
def init_files():
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(DEFAULT_TEMPLATES, f)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            json.dump({}, f)

# Load data
def load_templates():
    with open(TEMPLATES_FILE, 'r') as f:
        return json.load(f)

def load_bookings():
    with open(BOOKINGS_FILE, 'r') as f:
        return json.load(f)

# Save data
def save_templates(templates):
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(templates, f)

def save_bookings(bookings):
    with open(BOOKINGS_FILE, 'w') as f:
        json.dump(bookings, f)

# Initialize session state
def init_session_state():
    if 'bookings' not in st.session_state:
        st.session_state.bookings = load_bookings()
    if 'agent_id' not in st.session_state:
        st.session_state.agent_id = None
    if 'admin_mode' not in st.session_state:
        st.session_state.admin_mode = False
    if 'templates' not in st.session_state:
        st.session_state.templates = load_templates()
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True

# Admin functions
def admin_login(username, password):
    return username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password

def admin_interface():
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
            lunch_slots = st.text_area("Lunch Slots (comma separated):", 
                                      value=", ".join(template["lunch"]["slots"]))
            lunch_duration = st.number_input("Lunch Duration (minutes):", 
                                           value=template["lunch"]["duration"], min_value=1)
            
            # Early Tea settings
            st.subheader("Early Tea Break Settings")
            tea_early_slots = st.text_area("Early Tea Slots (comma separated):", 
                                         value=", ".join(template["tea_break_early"]["slots"]))
            tea_early_duration = st.number_input("Early Tea Duration (minutes):", 
                                               value=template["tea_break_early"]["duration"], min_value=1)
            tea_early_max = st.number_input("Max Early Tea Bookings per Agent:", 
                                          value=template["tea_break_early"]["max_bookings"] or 0)
            
            # Late Tea settings
            st.subheader("Late Tea Break Settings")
            tea_late_slots = st.text_area("Late Tea Slots (comma separated):", 
                                        value=", ".join(template["tea_break_late"]["slots"]))
            tea_late_duration = st.number_input("Late Tea Duration (minutes):", 
                                              value=template["tea_break_late"]["duration"], min_value=1)
            tea_late_max = st.number_input("Max Late Tea Bookings per Agent:", 
                                         value=template["tea_break_late"]["max_bookings"] or 0)
            
            # Last hour settings
            st.subheader("Last Hour Settings")
            last_hour_start = st.text_input("Last Hour Start Time:", value=template["last_hour"]["start"])
            last_hour_end = st.text_input("Last Hour End Time:", value=template["last_hour"]["end"])
            bio_duration = st.number_input("Bio Break Duration in Last Hour (minutes):", 
                                        value=template["last_hour"]["bio_break_duration"], min_value=1)
            
            if st.button("Update Template"):
                # Process slots
                template["lunch"]["slots"] = [s.strip() for s in lunch_slots.split(",")]
                template["lunch"]["duration"] = lunch_duration
                
                template["tea_break_early"]["slots"] = [s.strip() for s in tea_early_slots.split(",")]
                template["tea_break_early"]["duration"] = tea_early_duration
                template["tea_break_early"]["max_bookings"] = tea_early_max if tea_early_max > 0 else None
                
                template["tea_break_late"]["slots"] = [s.strip() for s in tea_late_slots.split(",")]
                template["tea_break_late"]["duration"] = tea_late_duration
                template["tea_break_late"]["max_bookings"] = tea_late_max if tea_late_max > 0 else None
                
                template["last_hour"]["start"] = last_hour_start
                template["last_hour"]["end"] = last_hour_end
                template["last_hour"]["bio_break_duration"] = bio_duration
                
                # Handle name change
                if new_name != selected_template:
                    st.session_state.templates[new_name] = st.session_state.templates.pop(selected_template)
                
                save_templates(st.session_state.templates)
                st.success("Template updated successfully!")
    
    # Create new template
    st.header("Create New Template")
    new_template_name = st.text_input("New Template Name:")
    if st.button("Create New Template") and new_template_name:
        if new_template_name in st.session_state.templates:
            st.warning("Template with this name already exists!")
        else:
            st.session_state.templates[new_template_name] = {
                "lunch": {
                    "slots": ["12:00", "12:30", "13:00"],
                    "duration": 30,
                    "max_bookings": None
                },
                "tea_break_early": {
                    "slots": ["10:00", "10:15", "10:30"],
                    "duration": 15,
                    "max_bookings": 1
                },
                "tea_break_late": {
                    "slots": ["15:00", "15:15", "15:30"],
                    "duration": 15,
                    "max_bookings": 1
                },
                "last_hour": {
                    "start": "17:00",
                    "end": "17:30",
                    "bio_break_duration": 5
                }
            }
            save_templates(st.session_state.templates)
            st.success(f"New template '{new_template_name}' created! You can now edit it.")
    
    # Delete template
    st.header("Delete Template")
    template_to_delete = st.selectbox("Select template to delete:", template_names)
    if st.button("Delete Template") and template_to_delete:
        if len(template_names) <= 1:
            st.warning("Cannot delete the last remaining template!")
        else:
            del st.session_state.templates[template_to_delete]
            save_templates(st.session_state.templates)
            st.success(f"Template '{template_to_delete}' deleted!")
    
    # View all bookings
    st.header("View All Bookings")
    for shift_name, shift_data in st.session_state.bookings.items():
        st.subheader(f"{shift_name} Bookings")
        df = pd.DataFrame([(b['agent'], bt, b['slot'], b['timestamp']) 
                          for bt, bookings in shift_data.items() 
                          for b in bookings],
                         columns=["Agent", "Break Type", "Time Slot", "Timestamp"])
        st.dataframe(df)

# Agent functions
def book_break(shift, break_type, slot):
    if shift not in st.session_state.bookings:
        st.session_state.bookings[shift] = {"lunch": [], "tea_break_early": [], "tea_break_late": []}
    
    # Check if user already booked this type of break
    user_bookings = [b for b in st.session_state.bookings[shift][break_type] if b["agent"] == st.session_state.agent_id]
    
    max_bookings = st.session_state.templates[shift][break_type]["max_bookings"]
    if max_bookings is not None and len(user_bookings) >= max_bookings:
        st.warning(f"You can only book {max_bookings} {break_type.replace('_', ' ')} per shift!")
        return
    
    # Add the booking
    booking = {
        "agent": st.session_state.agent_id,
        "slot": slot,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.bookings[shift][break_type].append(booking)
    save_bookings(st.session_state.bookings)
    st.success(f"Booked {break_type.replace('_', ' ')} at {slot}!")

def display_shift_bookings(shift):
    st.subheader(f"{shift} Bookings")
    
    if shift not in st.session_state.bookings:
        st.session_state.bookings[shift] = {"lunch": [], "tea_break_early": [], "tea_break_late": []}
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Lunch Breaks**")
        lunch_bookings = st.session_state.bookings[shift]["lunch"]
        if lunch_bookings:
            df = pd.DataFrame(lunch_bookings)
            st.dataframe(df[["agent", "slot"]], hide_index=True)
        else:
            st.write("No lunch bookings yet")
    
    with col2:
        st.write("**Early Tea Breaks**")
        tea_early_bookings = st.session_state.bookings[shift]["tea_break_early"]
        if tea_early_bookings:
            df = pd.DataFrame(tea_early_bookings)
            st.dataframe(df[["agent", "slot"]], hide_index=True)
        else:
            st.write("No early tea break bookings yet")
    
    with col3:
        st.write("**Late Tea Breaks**")
        tea_late_bookings = st.session_state.bookings[shift]["tea_break_late"]
        if tea_late_bookings:
            df = pd.DataFrame(tea_late_bookings)
            st.dataframe(df[["agent", "slot"]], hide_index=True)
        else:
            st.write("No late tea break bookings yet")

def agent_interface():
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
            lunch_slot = st.selectbox("Select lunch time:", 
                                    st.session_state.templates[shift]["lunch"]["slots"],
                                    key="lunch_select")
            if st.button("Book Lunch Break", key="lunch_btn"):
                book_break(shift, "lunch", lunch_slot)
        
        with col2:
            st.subheader("Early Tea Break")
            tea_early_slot = st.selectbox("Select early tea time:", 
                                         st.session_state.templates[shift]["tea_break_early"]["slots"],
                                         key="tea_early_select")
            if st.button("Book Early Tea Break", key="tea_early_btn"):
                book_break(shift, "tea_break_early", tea_early_slot)
        
        with col3:
            st.subheader("Late Tea Break")
            tea_late_slot = st.selectbox("Select late tea time:", 
                                        st.session_state.templates[shift]["tea_break_late"]["slots"],
                                        key="tea_late_select")
            if st.button("Book Late Tea Break", key="tea_late_btn"):
                book_break(shift, "tea_break_late", tea_late_slot)
    
    # Display rules
    st.markdown("---")
    st.subheader("Break Rules")
    st.write(f"**{shift} Rules:**")
    st.write(f"- Lunch duration: {st.session_state.templates[shift]['lunch']['duration']} minutes")
    st.write(f"- Tea break duration: {st.session_state.templates[shift]['tea_break_early']['duration']} minutes")
    st.write(f"- Only {st.session_state.templates[shift]['last_hour']['bio_break_duration']} minutes bio break is authorized in the last hour between {st.session_state.templates[shift]['last_hour']['start']} till {st.session_state.templates[shift]['last_hour']['end']}")
    st.write("- NO BREAK AFTER THE LAST HOUR END TIME!")
    st.write("- Breaks must be confirmed by RTA or Team Leaders")
    
    # Display current bookings
    st.markdown("---")
    display_shift_bookings(shift)

def main():
    init_files()
    init_session_state()
    
    # Login section
    if not st.session_state.agent_id and not st.session_state.admin_mode:
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
                if admin_login(admin_user, admin_pass):
                    st.session_state.admin_mode = True
                else:
                    st.error("Invalid admin credentials")
        
        if not st.session_state.agent_id and not st.session_state.admin_mode:
            st.warning("Please login to continue")
            return
    
    # Logout button
    if st.session_state.agent_id or st.session_state.admin_mode:
        if st.button("Logout"):
            st.session_state.agent_id = None
            st.session_state.admin_mode = False
            st.experimental_rerun()
    
    # Show appropriate interface
    if st.session_state.admin_mode:
        admin_interface()
    elif st.session_state.agent_id:
        agent_interface()

if __name__ == "__main__":
    main()
