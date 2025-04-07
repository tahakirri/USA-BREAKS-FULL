import streamlit as st
from datetime import datetime
import pandas as pd
import json
import os

# Default break templates with corrected structure
DEFAULT_TEMPLATES = {
    "2:00 PM Shift": {
        "lunch": {
            "slots": {
                "18:30": {"max_users": None},
                "19:00": {"max_users": None},
                "19:30": {"max_users": None},
                "20:00": {"max_users": None},
                "20:30": {"max_users": None}
            },
            "duration": 30,
            "max_bookings": None
        },
        "tea_break_early": {
            "slots": {
                "15:00": {"max_users": 1},
                "15:15": {"max_users": 1},
                "15:30": {"max_users": 1},
                "15:45": {"max_users": 1},
                "16:00": {"max_users": 1},
                "16:15": {"max_users": 1},
                "16:30": {"max_users": 1}
            },
            "duration": 15,
            "max_bookings": 1
        },
        "tea_break_late": {
            "slots": {
                "20:45": {"max_users": 1},
                "21:00": {"max_users": 1},
                "21:15": {"max_users": 1},
                "21:30": {"max_users": 1}
            },
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
            "slots": {
                "21:00": {"max_users": None},
                "21:30": {"max_users": None},
                "22:00": {"max_users": None},
                "22:30": {"max_users": None}
            },
            "duration": 30,
            "max_bookings": None
        },
        "tea_break_early": {
            "slots": {
                "19:00": {"max_users": 1},
                "19:15": {"max_users": 1},
                "19:30": {"max_users": 1},
                "19:45": {"max_users": 1},
                "20:00": {"max_users": 1},
                "20:15": {"max_users": 1},
                "20:30": {"max_users": 1},
                "20:45": {"max_users": 1}
            },
            "duration": 15,
            "max_bookings": 1
        },
        "tea_break_late": {
            "slots": {
                "00:00": {"max_users": 1},
                "00:15": {"max_users": 1},
                "00:30": {"max_users": 1},
                "00:45": {"max_users": 1},
                "01:00": {"max_users": 1},
                "01:15": {"max_users": 1},
                "01:30": {"max_users": 1}
            },
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

# Admin credentials
ADMIN_CREDENTIALS = {
    "admin": "admin123"
}

# File paths
TEMPLATES_FILE = "break_templates.json"
BOOKINGS_FILE = "bookings.json"

def migrate_template(templates):
    """Migrate old list-based slot structure to new dictionary format"""
    for shift, config in templates.items():
        for break_type in ["lunch", "tea_break_early", "tea_break_late"]:
            if isinstance(config[break_type]["slots"], list):
                # Convert list to dictionary format
                new_slots = {}
                for slot in config[break_type]["slots"]:
                    if break_type == "lunch":
                        new_slots[slot] = {"max_users": None}
                    else:
                        new_slots[slot] = {"max_users": 1}
                config[break_type]["slots"] = new_slots
    return templates

# Initialize data files
def init_files():
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump(DEFAULT_TEMPLATES, f)
    if not os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, 'w') as f:
            json.dump({}, f)

# Load data with migration
def load_templates():
    with open(TEMPLATES_FILE, 'r') as f:
        templates = json.load(f)
    return migrate_template(templates)

def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return {}
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
                                     value=", ".join(template["lunch"]["slots"].keys()))
            lunch_duration = st.number_input("Lunch Duration (minutes):", 
                                           value=template["lunch"]["duration"], min_value=1)
            lunch_max = st.number_input("Max Lunch Bookings per Agent:", 
                                      value=template["lunch"]["max_bookings"] or 0)
            
            # Early Tea settings
            st.subheader("Early Tea Break Settings")
            tea_early_slots = st.text_area("Early Tea Slots (comma separated):", 
                                         value=", ".join(template["tea_break_early"]["slots"].keys()))
            tea_early_duration = st.number_input("Early Tea Duration (minutes):", 
                                               value=template["tea_break_early"]["duration"], min_value=1)
            tea_early_max = st.number_input("Max Early Tea Bookings per Agent:", 
                                          value=template["tea_break_early"]["max_bookings"] or 0)
            
            # Late Tea settings
            st.subheader("Late Tea Break Settings")
            tea_late_slots = st.text_area("Late Tea Slots (comma separated):", 
                                        value=", ".join(template["tea_break_late"]["slots"].keys()))
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
                new_lunch_slots = {s.strip(): {"max_users": None} for s in lunch_slots.split(",")}
                for slot in new_lunch_slots:
                    if slot in template["lunch"]["slots"]:
                        new_lunch_slots[slot]["max_users"] = template["lunch"]["slots"][slot]["max_users"]
                template["lunch"]["slots"] = new_lunch_slots
                template["lunch"]["duration"] = lunch_duration
                template["lunch"]["max_bookings"] = lunch_max if lunch_max > 0 else None
                
                new_tea_early_slots = {s.strip(): {"max_users": 1} for s in tea_early_slots.split(",")}
                for slot in new_tea_early_slots:
                    if slot in template["tea_break_early"]["slots"]:
                        new_tea_early_slots[slot]["max_users"] = template["tea_break_early"]["slots"][slot]["max_users"]
                template["tea_break_early"]["slots"] = new_tea_early_slots
                template["tea_break_early"]["duration"] = tea_early_duration
                template["tea_break_early"]["max_bookings"] = tea_early_max if tea_early_max > 0 else None
                
                new_tea_late_slots = {s.strip(): {"max_users": 1} for s in tea_late_slots.split(",")}
                for slot in new_tea_late_slots:
                    if slot in template["tea_break_late"]["slots"]:
                        new_tea_late_slots[slot]["max_users"] = template["tea_break_late"]["slots"][slot]["max_users"]
                template["tea_break_late"]["slots"] = new_tea_late_slots
                template["tea_break_late"]["duration"] = tea_late_duration
                template["tea_break_late"]["max_bookings"] = tea_late_max if tea_late_max > 0 else None
                
                template["last_hour"]["start"] = last_hour_start
                template["last_hour"]["end"] = last_hour_end
                template["last_hour"]["bio_break_duration"] = bio_duration
                
                if new_name != selected_template:
                    st.session_state.templates[new_name] = st.session_state.templates.pop(selected_template)
                
                save_templates(st.session_state.templates)
                st.success("Template updated successfully!")
        
        # Edit slot-specific max users
        st.header("Edit Slot-Specific Maximum Users")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Lunch Break Slots")
            for slot, data in template["lunch"]["slots"].items():
                max_users = st.number_input(
                    f"Max users for {slot}:",
                    min_value=1,
                    value=data["max_users"] if data["max_users"] is not None else 0,
                    key=f"lunch_{slot}_max"
                )
                template["lunch"]["slots"][slot]["max_users"] = max_users if max_users > 0 else None
        
        with col2:
            st.subheader("Early Tea Break Slots")
            for slot, data in template["tea_break_early"]["slots"].items():
                max_users = st.number_input(
                    f"Max users for {slot}:",
                    min_value=1,
                    value=data["max_users"] if data["max_users"] is not None else 1,
                    key=f"tea_early_{slot}_max"
                )
                template["tea_break_early"]["slots"][slot]["max_users"] = max_users if max_users > 0 else None
        
        with col3:
            st.subheader("Late Tea Break Slots")
            for slot, data in template["tea_break_late"]["slots"].items():
                max_users = st.number_input(
                    f"Max users for {slot}:",
                    min_value=1,
                    value=data["max_users"] if data["max_users"] is not None else 1,
                    key=f"tea_late_{slot}_max"
                )
                template["tea_break_late"]["slots"][slot]["max_users"] = max_users if max_users > 0 else None
        
        if st.button("Save Slot Limits"):
            save_templates(st.session_state.templates)
            st.success("Slot limits updated successfully!")
    
    # Create new template
    st.header("Create New Template")
    new_template_name = st.text_input("New Template Name:")
    if st.button("Create New Template") and new_template_name:
        if new_template_name in st.session_state.templates:
            st.warning("Template with this name already exists!")
        else:
            st.session_state.templates[new_template_name] = {
                "lunch": {
                    "slots": {
                        "12:00": {"max_users": None},
                        "12:30": {"max_users": None},
                        "13:00": {"max_users": None}
                    },
                    "duration": 30,
                    "max_bookings": None
                },
                "tea_break_early": {
                    "slots": {
                        "10:00": {"max_users": 1},
                        "10:15": {"max_users": 1},
                        "10:30": {"max_users": 1}
                    },
                    "duration": 15,
                    "max_bookings": 1
                },
                "tea_break_late": {
                    "slots": {
                        "15:00": {"max_users": 1},
                        "15:15": {"max_users": 1},
                        "15:30": {"max_users": 1}
                    },
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
    
    user_bookings = [b for b in st.session_state.bookings[shift][break_type] if b["agent"] == st.session_state.agent_id]
    
    max_bookings = st.session_state.templates[shift][break_type]["max_bookings"]
    if max_bookings is not None and len(user_bookings) >= max_bookings:
        st.warning(f"You can only book {max_bookings} {break_type.replace('_', ' ')} per shift!")
        return
    
    slot_max = st.session_state.templates[shift][break_type]["slots"][slot]["max_users"]
    if slot_max is not None:
        slot_bookings = [b for b in st.session_state.bookings[shift][break_type] if b["slot"] == slot]
        if len(slot_bookings) >= slot_max:
            st.warning(f"This time slot ({slot}) is already full (max {slot_max} users)!")
            return
    
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
            df["Max Users"] = df["slot"].apply(
                lambda x: st.session_state.templates[shift]["lunch"]["slots"][x]["max_users"] or "Unlimited"
            )
            df["Current Users"] = df["slot"].apply(
                lambda x: len([b for b in lunch_bookings if b["slot"] == x])
            )
            st.dataframe(df[["agent", "slot", "Current Users", "Max Users"]], hide_index=True)
        else:
            st.write("No lunch bookings yet")
    
    with col2:
        st.write("**Early Tea Breaks**")
        tea_early_bookings = st.session_state.bookings[shift]["tea_break_early"]
        if tea_early_bookings:
            df = pd.DataFrame(tea_early_bookings)
            df["Max Users"] = df["slot"].apply(
                lambda x: st.session_state.templates[shift]["tea_break_early"]["slots"][x]["max_users"] or "Unlimited"
            )
            df["Current Users"] = df["slot"].apply(
                lambda x: len([b for b in tea_early_bookings if b["slot"] == x])
            )
            st.dataframe(df[["agent", "slot", "Current Users", "Max Users"]], hide_index=True)
        else:
            st.write("No early tea break bookings yet")
    
    with col3:
        st.write("**Late Tea Breaks**")
        tea_late_bookings = st.session_state.bookings[shift]["tea_break_late"]
        if tea_late_bookings:
            df = pd.DataFrame(tea_late_bookings)
            df["Max Users"] = df["slot"].apply(
                lambda x: st.session_state.templates[shift]["tea_break_late"]["slots"][x]["max_users"] or "Unlimited"
            )
            df["Current Users"] = df["slot"].apply(
                lambda x: len([b for b in tea_late_bookings if b["slot"] == x])
            )
            st.dataframe(df[["agent", "slot", "Current Users", "Max Users"]], hide_index=True)
        else:
            st.write("No late tea break bookings yet")

def agent_interface():
    st.title("Agent Break Booking System")
    
    shift_names = list(st.session_state.templates.keys())
    shift = st.radio("Select your shift:", shift_names, horizontal=True)
    
    st.header(f"Book Breaks for {shift}")
    
    with st.expander("Book Your Breaks", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Lunch Break")
            available_lunch_slots = []
            for slot in st.session_state.templates[shift]["lunch"]["slots"]:
                max_users = st.session_state.templates[shift]["lunch"]["slots"][slot]["max_users"]
                if max_users is None:
                    available_lunch_slots.append(slot)
                else:
                    current_users = len([b for b in st.session_state.bookings.get(shift, {}).get("lunch", []) if b["slot"] == slot])
                    if current_users < max_users:
                        available_lunch_slots.append(slot)
            
            if available_lunch_slots:
                lunch_slot = st.selectbox("Select lunch time:", available_lunch_slots, key="lunch_select")
                if st.button("Book Lunch Break", key="lunch_btn"):
                    book_break(shift, "lunch", lunch_slot)
            else:
                st.warning("No available lunch slots!")
        
        with col2:
            st.subheader("Early Tea Break")
            available_tea_early_slots = []
            for slot in st.session_state.templates[shift]["tea_break_early"]["slots"]:
                max_users = st.session_state.templates[shift]["tea_break_early"]["slots"][slot]["max_users"]
                if max_users is None:
                    available_tea_early_slots.append(slot)
                else:
                    current_users = len([b for b in st.session_state.bookings.get(shift, {}).get("tea_break_early", []) if b["slot"] == slot])
                    if current_users < max_users:
                        available_tea_early_slots.append(slot)
            
            if available_tea_early_slots:
                tea_early_slot = st.selectbox("Select early tea time:", available_tea_early_slots, key="tea_early_select")
                if st.button("Book Early Tea Break", key="tea_early_btn"):
                    book_break(shift, "tea_break_early", tea_early_slot)
            else:
                st.warning("No available early tea slots!")
        
        with col3:
            st.subheader("Late Tea Break")
            available_tea_late_slots = []
            for slot in st.session_state.templates[shift]["tea_break_late"]["slots"]:
                max_users = st.session_state.templates[shift]["tea_break_late"]["slots"][slot]["max_users"]
                if max_users is None:
                    available_tea_late_slots.append(slot)
                else:
                    current_users = len([b for b in st.session_state.bookings.get(shift, {}).get("tea_break_late", []) if b["slot"] == slot])
                    if current_users < max_users:
                        available_tea_late_slots.append(slot)
            
            if available_tea_late_slots:
                tea_late_slot = st.selectbox("Select late tea time:", available_tea_late_slots, key="tea_late_select")
                if st.button("Book Late Tea Break", key="tea_late_btn"):
                    book_break(shift, "tea_break_late", tea_late_slot)
            else:
                st.warning("No available late tea slots!")
    
    st.markdown("---")
    st.subheader("Break Rules")
    st.write(f"**{shift} Rules:**")
    st.write(f"- Lunch duration: {st.session_state.templates[shift]['lunch']['duration']} minutes")
    st.write(f"- Tea break duration: {st.session_state.templates[shift]['tea_break_early']['duration']} minutes")
    st.write(f"- Only {st.session_state.templates[shift]['last_hour']['bio_break_duration']} minutes bio break is authorized in the last hour between {st.session_state.templates[shift]['last_hour']['start']} till {st.session_state.templates[shift]['last_hour']['end']}")
    st.write("- NO BREAK AFTER THE LAST HOUR END TIME!")
    st.write("- Breaks must be confirmed by RTA or Team Leaders")
    
    st.markdown("---")
    display_shift_bookings(shift)

def main():
    init_files()
    init_session_state()
    
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
    
    if st.session_state.agent_id or st.session_state.admin_mode:
        if st.button("Logout"):
            st.session_state.agent_id = None
            st.session_state.admin_mode = False
            st.experimental_rerun()
    
    if st.session_state.admin_mode:
        admin_interface()
    elif st.session_state.agent_id:
        agent_interface()

if __name__ == "__main__":
    main()
