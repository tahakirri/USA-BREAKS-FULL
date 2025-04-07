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
                "early_tea_breaks": {
                    "16:00": {"slots": 5, "booked": []},
                    "16:15": {"slots": 5, "booked": []},
                    "16:30": {"slots": 5, "booked": []},
                    "16:45": {"slots": 5, "booked": []},
                    "17:00": {"slots": 5, "booked": []},
                    "17:15": {"slots": 5, "booked": []},
                    "17:30": {"slots": 5, "booked": []},
                },
                "lunch_breaks": {
                    "19:00": {"slots": 5, "booked": []},
                    "19:30": {"slots": 5, "booked": []},
                    "20:00": {"slots": 5, "booked": []},
                    "20:30": {"slots": 5, "booked": []},
                    "21:00": {"slots": 5, "booked": []},
                    "21:30": {"slots": 5, "booked": []},
                },
                "late_tea_breaks": {
                    "21:30": {"slots": 5, "booked": []},
                    "21:45": {"slots": 5, "booked": []},
                    "22:00": {"slots": 5, "booked": []},
                    "22:15": {"slots": 5, "booked": []},
                    "22:30": {"slots": 5, "booked": []},
                },
                "last_hour": "22:00-22:30",
                "bio_only": True
            },
            "6pm_shift": {
                "name": "LM US ENG 6:00 PM shift",
                "early_tea_breaks": {
                    "19:00": {"slots": 5, "booked": []},
                    "19:15": {"slots": 5, "booked": []},
                    "19:30": {"slots": 5, "booked": []},
                    "19:45": {"slots": 5, "booked": []},
                    "20:00": {"slots": 5, "booked": []},
                    "20:15": {"slots": 5, "booked": []},
                    "20:30": {"slots": 5, "booked": []},
                    "20:45": {"slots": 5, "booked": []},
                },
                "lunch_breaks": {
                    "21:00": {"slots": 5, "booked": []},
                    "21:30": {"slots": 5, "booked": []},
                    "22:00": {"slots": 5, "booked": []},
                    "22:30": {"slots": 5, "booked": []},
                },
                "late_tea_breaks": {
                    "00:00": {"slots": 5, "booked": []},
                    "00:15": {"slots": 5, "booked": []},
                    "00:30": {"slots": 5, "booked": []},
                    "00:45": {"slots": 5, "booked": []},
                    "01:00": {"slots": 5, "booked": []},
                    "01:15": {"slots": 5, "booked": []},
                    "01:30": {"slots": 5, "booked": []},
                },
                "last_hour": "02:00-02:30",
                "bio_only": True
            }
        },
        "agents": {},
        "admin_password": "admin123"
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
    
    if not is_admin():
        password = st.text_input("Enter Admin Password", type="password")
        if password == data["admin_password"]:
            st.session_state["is_admin"] = True
            st.rerun()
        elif password:
            st.error("Incorrect password")
        return
    
    st.success("Logged in as Admin")
    
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
    
    shift = st.selectbox("Select Shift", list(data["shifts"].keys()), 
                        format_func=lambda x: data["shifts"][x]["name"])
    
    with st.expander("Manage Early Tea Breaks"):
        st.write("Current Early Tea Breaks:")
        breaks_df = pd.DataFrame([
            {"Time": time, "Slots": details["slots"], "Booked": len(details["booked"])}
            for time, details in data["shifts"][shift]["early_tea_breaks"].items()
        ])
        st.dataframe(breaks_df)
        
        new_break_time = st.text_input("Add New Early Tea Break (HH:MM)")
        new_break_slots = st.number_input("Slots", min_value=1, value=5, key="early_tea_slots")
        if st.button("Add Early Tea Break") and new_break_time:
            if new_break_time in data["shifts"][shift]["early_tea_breaks"]:
                st.error("Break time already exists")
            else:
                data["shifts"][shift]["early_tea_breaks"][new_break_time] = {
                    "slots": new_break_slots,
                    "booked": []
                }
                save_data(data)
                st.success("Break added")
                st.rerun()
        
        break_to_remove = st.selectbox("Remove Early Tea Break", 
                                     list(data["shifts"][shift]["early_tea_breaks"].keys()))
        if st.button("Remove Early Tea Break"):
            if len(data["shifts"][shift]["early_tea_breaks"][break_to_remove]["booked"]) > 0:
                st.error("Cannot remove break with booked agents")
            else:
                del data["shifts"][shift]["early_tea_breaks"][break_to_remove]
                save_data(data)
                st.success("Break removed")
                st.rerun()
    
    with st.expander("Manage Lunch Breaks"):
        st.write("Current Lunch Breaks:")
        lunch_df = pd.DataFrame([
            {"Time": time, "Slots": details["slots"], "Booked": len(details["booked"])}
            for time, details in data["shifts"][shift]["lunch_breaks"].items()
        ])
        st.dataframe(lunch_df)
        
        new_lunch_time = st.text_input("Add New Lunch Break (HH:MM)")
        new_lunch_slots = st.number_input("Slots", min_value=1, value=5, key="lunch_slots")
        if st.button("Add Lunch Break") and new_lunch_time:
            if new_lunch_time in data["shifts"][shift]["lunch_breaks"]:
                st.error("Lunch time already exists")
            else:
                data["shifts"][shift]["lunch_breaks"][new_lunch_time] = {
                    "slots": new_lunch_slots,
                    "booked": []
                }
                save_data(data)
                st.success("Lunch break added")
                st.rerun()
        
        lunch_to_remove = st.selectbox("Remove Lunch Break", 
                                     list(data["shifts"][shift]["lunch_breaks"].keys()))
        if st.button("Remove Lunch Break"):
            if len(data["shifts"][shift]["lunch_breaks"][lunch_to_remove]["booked"]) > 0:
                st.error("Cannot remove break with booked agents")
            else:
                del data["shifts"][shift]["lunch_breaks"][lunch_to_remove]
                save_data(data)
                st.success("Lunch break removed")
                st.rerun()
    
    with st.expander("Manage Late Tea Breaks"):
        st.write("Current Late Tea Breaks:")
        late_df = pd.DataFrame([
            {"Time": time, "Slots": details["slots"], "Booked": len(details["booked"])}
            for time, details in data["shifts"][shift]["late_tea_breaks"].items()
        ])
        st.dataframe(late_df)
        
        new_late_time = st.text_input("Add New Late Tea Break (HH:MM)")
        new_late_slots = st.number_input("Slots", min_value=1, value=5, key="late_tea_slots")
        if st.button("Add Late Tea Break") and new_late_time:
            if new_late_time in data["shifts"][shift]["late_tea_breaks"]:
                st.error("Break time already exists")
            else:
                data["shifts"][shift]["late_tea_breaks"][new_late_time] = {
                    "slots": new_late_slots,
                    "booked": []
                }
                save_data(data)
                st.success("Late tea break added")
                st.rerun()
        
        late_to_remove = st.selectbox("Remove Late Tea Break", 
                                    list(data["shifts"][shift]["late_tea_breaks"].keys()))
        if st.button("Remove Late Tea Break"):
            if len(data["shifts"][shift]["late_tea_breaks"][late_to_remove]["booked"]) > 0:
                st.error("Cannot remove break with booked agents")
            else:
                del data["shifts"][shift]["late_tea_breaks"][late_to_remove]
                save_data(data)
                st.success("Late tea break removed")
                st.rerun()
    
    with st.expander("Edit Shift Rules"):
        last_hour = st.text_input("Last Hour (HH:MM-HH:MM)", 
                                value=data["shifts"][shift]["last_hour"])
        bio_only = st.checkbox("Bio Breaks Only in Last Hour", 
                             value=data["shifts"][shift]["bio_only"])
        if st.button("Update Rules"):
            data["shifts"][shift]["last_hour"] = last_hour
            data["shifts"][shift]["bio_only"] = bio_only
            save_data(data)
            st.success("Rules updated")

# Agent booking interface
def agent_booking(data, shift_key):
    shift = data["shifts"][shift_key]
    st.title(shift["name"])
    
    st.warning(f"""
    **RULES:**
    - NO BREAK IN THE LAST HOUR WILL BE AUTHORIZED
    - ONLY 5 MINUTES BIO IS AUTHORIZED IN THE LAST HOUR BETWEEN {shift["last_hour"]}
    - NO BREAK AFTER {shift["last_hour"].split('-')[1]} !!!
    - BREAKS SHOULD BE TAKEN AT THE NOTED TIME AND NEED TO BE CONFIRMED FROM RTA OR TEAM LEADERS
    - Each agent must book:
      * 1 Early Tea Break
      * 1 Lunch Break
      * 1 Late Tea Break
    """)
    
    agent_id = st.text_input("Enter Your Agent ID")
    if not agent_id:
        return
    
    # Initialize agent data if not exists
    if agent_id not in data["agents"]:
        data["agents"][agent_id] = {
            "early_tea": None,
            "lunch": None,
            "late_tea": None,
            "shift": shift_key
        }
        save_data(data)
    
    # Safely get existing bookings
    agent_data = data["agents"].get(agent_id, {
        "early_tea": None,
        "lunch": None,
        "late_tea": None,
        "shift": shift_key
    })
    
    existing_early_tea = agent_data["early_tea"]
    existing_lunch = agent_data["lunch"]
    existing_late_tea = agent_data["late_tea"]
    
    # Display current bookings
    if existing_early_tea or existing_lunch or existing_late_tea:
        st.subheader("Your Current Bookings")
        if existing_early_tea:
            st.write(f"Early Tea Break: {existing_early_tea}")
        if existing_lunch:
            st.write(f"Lunch Break: {existing_lunch}")
        if existing_late_tea:
            st.write(f"Late Tea Break: {existing_late_tea}")
        
        if st.button("Cancel All Bookings"):
            # Remove from early tea breaks
            if existing_early_tea in shift["early_tea_breaks"]:
                if agent_id in shift["early_tea_breaks"][existing_early_tea]["booked"]:
                    shift["early_tea_breaks"][existing_early_tea]["booked"].remove(agent_id)
            
            # Remove from lunch breaks
            if existing_lunch in shift["lunch_breaks"]:
                if agent_id in shift["lunch_breaks"][existing_lunch]["booked"]:
                    shift["lunch_breaks"][existing_lunch]["booked"].remove(agent_id)
            
            # Remove from late tea breaks
            if existing_late_tea in shift["late_tea_breaks"]:
                if agent_id in shift["late_tea_breaks"][existing_late_tea]["booked"]:
                    shift["late_tea_breaks"][existing_late_tea]["booked"].remove(agent_id)
            
            # Reset agent data
            data["agents"][agent_id] = {
                "early_tea": None,
                "lunch": None,
                "late_tea": None,
                "shift": shift_key
            }
            save_data(data)
            st.success("All bookings canceled")
            st.rerun()
        return
    
    # Determine which break to book next
    if not existing_early_tea:
        book_early_tea_break(data, shift, agent_id)
    elif not existing_lunch:
        book_lunch_break(data, shift, agent_id)
    elif not existing_late_tea:
        book_late_tea_break(data, shift, agent_id)
    else:
        st.success("You have booked all your required breaks!")

def book_early_tea_break(data, shift, agent_id):
    st.subheader("Book Early Tea Break")
    for time_slot, details in sorted(shift["early_tea_breaks"].items()):
        slots_available = details["slots"] - len(details["booked"])
        if slots_available > 0:
            if st.button(f"{time_slot} ({slots_available} slots available)"):
                details["booked"].append(agent_id)
                data["agents"][agent_id]["early_tea"] = time_slot
                save_data(data)
                st.success(f"Early tea break booked at {time_slot}")
                st.rerun()
        else:
            st.write(f"{time_slot} - FULL")

def book_lunch_break(data, shift, agent_id):
    st.subheader("Book Lunch Break")
    for time_slot, details in sorted(shift["lunch_breaks"].items()):
        slots_available = details["slots"] - len(details["booked"])
        if slots_available > 0:
            if st.button(f"{time_slot} ({slots_available} slots available)"):
                details["booked"].append(agent_id)
                data["agents"][agent_id]["lunch"] = time_slot
                save_data(data)
                st.success(f"Lunch break booked at {time_slot}")
                st.rerun()
        else:
            st.write(f"{time_slot} - FULL")

def book_late_tea_break(data, shift, agent_id):
    st.subheader("Book Late Tea Break")
    for time_slot, details in sorted(shift["late_tea_breaks"].items()):
        slots_available = details["slots"] - len(details["booked"])
        if slots_available > 0:
            if st.button(f"{time_slot} ({slots_available} slots available)"):
                details["booked"].append(agent_id)
                data["agents"][agent_id]["late_tea"] = time_slot
                save_data(data)
                st.success(f"Late tea break booked at {time_slot}")
                st.rerun()
        else:
            st.write(f"{time_slot} - FULL")

# Main app
def main():
    st.set_page_config(page_title="Break Booking System", layout="wide")
    data = load_data()
    
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
