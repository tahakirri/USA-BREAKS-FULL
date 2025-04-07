import streamlit as st
import pandas as pd
from datetime import datetime, time
import json
import os

# Constants
DATA_FILE = "break_data.json"
SHIFT_1_START = time(15, 0)  # 3:00 PM
SHIFT_2_START = time(18, 0)  # 6:00 PM

# Initialize data structure
def init_data():
    return {
        "shifts": {
            "3pm_shift": {
                "name": "LM US ENG SUNDAY 3:00 PM shift",
                "tea_breaks": {
                    "16:00": {"slots": 5, "booked": []},
                    "16:15": {"slots": 5, "booked": []},
                    "16:30": {"slots": 5, "booked": []},
                    "16:45": {"slots": 5, "booked": []},
                    "17:00": {"slots": 5, "booked": []},
                    "17:15": {"slots": 5, "booked": []},
                    "17:30": {"slots": 5, "booked": []},
                    "21:30": {"slots": 5, "booked": []},
                    "21:45": {"slots": 5, "booked": []},
                    "22:00": {"slots": 5, "booked": []},
                    "22:15": {"slots": 5, "booked": []},
                    "22:30": {"slots": 5, "booked": []},
                },
                "lunch_breaks": {
                    "19:00": {"slots": 5, "booked": []},
                    "19:30": {"slots": 5, "booked": []},
                    "20:00": {"slots": 5, "booked": []},
                    "20:30": {"slots": 5, "booked": []},
                    "21:00": {"slots": 5, "booked": []},
                    "21:30": {"slots": 5, "booked": []},
                },
                "last_hour": "22:00-22:30",
                "bio_only": True
            },
            "6pm_shift": {
                "name": "LM US ENG 6:00 PM shift",
                "tea_breaks": {
                    "19:00": {"slots": 5, "booked": []},
                    "19:15": {"slots": 5, "booked": []},
                    "19:30": {"slots": 5, "booked": []},
                    "19:45": {"slots": 5, "booked": []},
                    "20:00": {"slots": 5, "booked": []},
                    "20:15": {"slots": 5, "booked": []},
                    "20:30": {"slots": 5, "booked": []},
                    "20:45": {"slots": 5, "booked": []},
                    "00:00": {"slots": 5, "booked": []},
                    "00:15": {"slots": 5, "booked": []},
                    "00:30": {"slots": 5, "booked": []},
                    "00:45": {"slots": 5, "booked": []},
                    "01:00": {"slots": 5, "booked": []},
                    "01:15": {"slots": 5, "booked": []},
                    "01:30": {"slots": 5, "booked": []},
                },
                "lunch_breaks": {
                    "21:00": {"slots": 5, "booked": []},
                    "21:30": {"slots": 5, "booked": []},
                    "22:00": {"slots": 5, "booked": []},
                    "22:30": {"slots": 5, "booked": []},
                },
                "last_hour": "02:00-02:30",
                "bio_only": True
            }
        },
        "agents": {},
        "admin_password": "admin123"  # Change this in production!
    }

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    else:
        data = init_data()
        save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Helper functions
def get_current_shift():
    now = datetime.now().time()
    if SHIFT_1_START <= now < SHIFT_2_START:
        return "3pm_shift"
    else:
        return "6pm_shift"

def is_admin():
    return st.session_state.get("is_admin", False)

# Admin functions
def admin_panel(data):
    st.title("Admin Panel")
    
    # Password protection
    if not is_admin():
        password = st.text_input("Enter Admin Password", type="password")
        if password == data["admin_password"]:
            st.session_state["is_admin"] = True
            st.rerun()
        elif password:
            st.error("Incorrect password")
        return
    
    st.success("Logged in as Admin")
    
    # Change password
    with st.expander("Change Admin Password"):
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        if st.button("Update Password"):
            if new_pass == confirm_pass:
                data["admin_password"] = new_pass
                save_data(data)
                st.success("Password updated successfully")
            else:
                st.error("Passwords don't match")
    
    # Shift selection
    shift = st.selectbox("Select Shift", list(data["shifts"].keys()), 
                        format_func=lambda x: data["shifts"][x]["name"])
    
    # Bulk edit tea breaks
    with st.expander("Bulk Edit Tea Breaks"):
        st.write("Current Tea Breaks:")
        tea_breaks_df = pd.DataFrame([
            {"Time": time, "Slots": details["slots"], "Booked": len(details["booked"])}
            for time, details in data["shifts"][shift]["tea_breaks"].items()
        ])
        st.dataframe(tea_breaks_df)
        
        # Add new tea breaks
        new_break_time = st.text_input("Add New Tea Break Time (HH:MM format)")
        new_break_slots = st.number_input("Tea Break Slots", min_value=1, value=5)
        if st.button("Add Tea Break") and new_break_time:
            if new_break_time in data["shifts"][shift]["tea_breaks"]:
                st.error("Tea break time already exists")
            else:
                data["shifts"][shift]["tea_breaks"][new_break_time] = {
                    "slots": new_break_slots,
                    "booked": []
                }
                save_data(data)
                st.success("Tea break added")
                st.rerun()
        
        # Remove tea breaks
        break_to_remove = st.selectbox("Select Tea Break to Remove", 
                                      list(data["shifts"][shift]["tea_breaks"].keys()))
        if st.button("Remove Tea Break"):
            if len(data["shifts"][shift]["tea_breaks"][break_to_remove]["booked"]) > 0:
                st.error("Cannot remove break with booked agents")
            else:
                del data["shifts"][shift]["tea_breaks"][break_to_remove]
                save_data(data)
                st.success("Tea break removed")
                st.rerun()
    
    # Bulk edit lunch breaks
    with st.expander("Bulk Edit Lunch Breaks"):
        st.write("Current Lunch Breaks:")
        lunch_breaks_df = pd.DataFrame([
            {"Time": time, "Slots": details["slots"], "Booked": len(details["booked"])}
            for time, details in data["shifts"][shift]["lunch_breaks"].items()
        ])
        st.dataframe(lunch_breaks_df)
        
        # Add new lunch breaks
        new_lunch_time = st.text_input("Add New Lunch Break Time (HH:MM format)")
        new_lunch_slots = st.number_input("Lunch Break Slots", min_value=1, value=5)
        if st.button("Add Lunch Break") and new_lunch_time:
            if new_lunch_time in data["shifts"][shift]["lunch_breaks"]:
                st.error("Lunch break time already exists")
            else:
                data["shifts"][shift]["lunch_breaks"][new_lunch_time] = {
                    "slots": new_lunch_slots,
                    "booked": []
                }
                save_data(data)
                st.success("Lunch break added")
                st.rerun()
        
        # Remove lunch breaks
        lunch_to_remove = st.selectbox("Select Lunch Break to Remove", 
                                     list(data["shifts"][shift]["lunch_breaks"].keys()))
        if st.button("Remove Lunch Break"):
            if len(data["shifts"][shift]["lunch_breaks"][lunch_to_remove]["booked"]) > 0:
                st.error("Cannot remove break with booked agents")
            else:
                del data["shifts"][shift]["lunch_breaks"][lunch_to_remove]
                save_data(data)
                st.success("Lunch break removed")
                st.rerun()
    
    # Edit last hour rules
    with st.expander("Edit Last Hour Rules"):
        last_hour = st.text_input("Last Hour (format: HH:MM-HH:MM)", 
                                value=data["shifts"][shift]["last_hour"])
        bio_only = st.checkbox("Bio Breaks Only in Last Hour", 
                             value=data["shifts"][shift]["bio_only"])
        if st.button("Update Last Hour Rules"):
            data["shifts"][shift]["last_hour"] = last_hour
            data["shifts"][shift]["bio_only"] = bio_only
            save_data(data)
            st.success("Rules updated")

# Agent booking interface
def agent_booking(data, shift_key):
    shift = data["shifts"][shift_key]
    st.title(shift["name"])
    
    # Display rules
    st.warning(f"""
    **RULES:**
    - NO BREAK IN THE LAST HOUR WILL BE AUTHORIZED
    - ONLY 5 MINUTES BIO IS AUTHORIZED IN THE LAST HOUR BETWEEN {shift["last_hour"]}
    - NO BREAK AFTER {shift["last_hour"].split('-')[1]} !!!
    - BREAKS SHOULD BE TAKEN AT THE NOTED TIME AND NEED TO BE CONFIRMED FROM RTA OR TEAM LEADERS
    - Each agent can book ONE first tea break, ONE second tea break, and ONE lunch break
    """)
    
    # Agent ID input
    agent_id = st.text_input("Enter Your Agent ID")
    if not agent_id:
        return
    
    # Initialize agent data if not exists
    if agent_id not in data["agents"]:
        data["agents"][agent_id] = {
            "first_tea_break": None,
            "second_tea_break": None,
            "lunch_break": None,
            "shift": shift_key
        }
    
    # Check existing bookings
    existing_first_tea = data["agents"][agent_id]["first_tea_break"]
    existing_second_tea = data["agents"][agent_id]["second_tea_break"]
    existing_lunch = data["agents"][agent_id]["lunch_break"]
    
    # Display current bookings
    if existing_first_tea or existing_second_tea or existing_lunch:
        st.subheader("Your Current Bookings")
        if existing_first_tea:
            st.write(f"First Tea Break: {existing_first_tea}")
        if existing_second_tea:
            st.write(f"Second Tea Break: {existing_second_tea}")
        if existing_lunch:
            st.write(f"Lunch Break: {existing_lunch}")
        
        if st.button("Cancel All Bookings"):
            # Remove from tea breaks
            if existing_first_tea and existing_first_tea in shift["tea_breaks"]:
                if agent_id in shift["tea_breaks"][existing_first_tea]["booked"]:
                    shift["tea_breaks"][existing_first_tea]["booked"].remove(agent_id)
            
            if existing_second_tea and existing_second_tea in shift["tea_breaks"]:
                if agent_id in shift["tea_breaks"][existing_second_tea]["booked"]:
                    shift["tea_breaks"][existing_second_tea]["booked"].remove(agent_id)
            
            # Remove from lunch breaks
            if existing_lunch and existing_lunch in shift["lunch_breaks"]:
                if agent_id in shift["lunch_breaks"][existing_lunch]["booked"]:
                    shift["lunch_breaks"][existing_lunch]["booked"].remove(agent_id)
            
            # Reset agent data
            data["agents"][agent_id] = {
                "first_tea_break": None,
                "second_tea_break": None,
                "lunch_break": None,
                "shift": shift_key
            }
            save_data(data)
            st.success("All bookings canceled")
            st.rerun()
        return
    
    # Determine which breaks still need to be booked
    booking_stage = None
    if not existing_first_tea:
        booking_stage = "first_tea"
    elif not existing_second_tea:
        booking_stage = "second_tea"
    elif not existing_lunch:
        booking_stage = "lunch"
    else:
        st.success("You have booked all your breaks!")
        return
    
    # Book first tea break
    if booking_stage == "first_tea":
        st.subheader("Book First Tea Break")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Early Tea Breaks**")
            for time_slot, details in sorted(shift["tea_breaks"].items()):
                # Simple way to split breaks between first and second tea breaks
                if int(time_slot.split(':')[0]) < 20:  # Before 8 PM
                    slots_available = details["slots"] - len(details["booked"])
                    if slots_available > 0:
                        if st.button(f"{time_slot} ({slots_available} slots available)"):
                            details["booked"].append(agent_id)
                            data["agents"][agent_id]["first_tea_break"] = time_slot
                            save_data(data)
                            st.success(f"First tea break booked at {time_slot}")
                            st.rerun()
                    else:
                        st.write(f"{time_slot} - FULL")
    
    # Book second tea break
    elif booking_stage == "second_tea":
        st.subheader("Book Second Tea Break")
        col1, col2 = st.columns(2)
        
        with col2:
            st.write("**Late Tea Breaks**")
            for time_slot, details in sorted(shift["tea_breaks"].items()):
                if int(time_slot.split(':')[0]) >= 20:  # 8 PM and after
                    slots_available = details["slots"] - len(details["booked"])
                    if slots_available > 0:
                        if st.button(f"{time_slot} ({slots_available} slots available)"):
                            details["booked"].append(agent_id)
                            data["agents"][agent_id]["second_tea_break"] = time_slot
                            save_data(data)
                            st.success(f"Second tea break booked at {time_slot}")
                            st.rerun()
                    else:
                        st.write(f"{time_slot} - FULL")
    
    # Book lunch break
    elif booking_stage == "lunch":
        st.subheader("Book Lunch Break")
        for time_slot, details in sorted(shift["lunch_breaks"].items()):
            slots_available = details["slots"] - len(details["booked"])
            if slots_available > 0:
                if st.button(f"{time_slot} ({slots_available} slots available)"):
                    details["booked"].append(agent_id)
                    data["agents"][agent_id]["lunch_break"] = time_slot
                    save_data(data)
                    st.success(f"Lunch break booked at {time_slot}")
                    st.rerun()
            else:
                st.write(f"{time_slot} - FULL")

# Main app
def main():
    st.set_page_config(page_title="Break Booking System", layout="wide")
    data = load_data()
    
    # Admin login button
    if st.sidebar.button("Admin Login"):
        st.session_state["show_admin"] = True
    
    # Show admin panel or agent interface
    if st.session_state.get("show_admin", False):
        admin_panel(data)
        if st.sidebar.button("Back to Agent View"):
            st.session_state["show_admin"] = False
            st.rerun()
    else:
        # Auto-detect shift or let user choose
        current_shift = get_current_shift()
        shift_choice = st.sidebar.radio("Select Shift", 
                                      [data["shifts"]["3pm_shift"]["name"], 
                                       data["shifts"]["6pm_shift"]["name"]],
                                      index=0 if current_shift == "3pm_shift" else 1)
        
        shift_key = "3pm_shift" if shift_choice == data["shifts"]["3pm_shift"]["name"] else "6pm_shift"
        agent_booking(data, shift_key)

if __name__ == "__main__":
    main()
