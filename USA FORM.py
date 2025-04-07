import streamlit as st
from datetime import datetime
import pandas as pd

# Break rules for each shift
shift_rules = {
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

# Initialize session state
if 'bookings' not in st.session_state:
    st.session_state.bookings = {
        "2:00 PM Shift": {"lunch": [], "tea_break_early": [], "tea_break_late": []},
        "6:00 PM Shift": {"lunch": [], "tea_break_early": [], "tea_break_late": []}
    }

if 'agent_id' not in st.session_state:
    st.session_state.agent_id = None

def book_break(shift, break_type, slot):
    # Check if user already booked this type of break
    user_bookings = [b for b in st.session_state.bookings[shift][break_type] if b["agent"] == st.session_state.agent_id]
    
    max_bookings = shift_rules[shift][break_type]["max_bookings"]
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
    st.success(f"Booked {break_type.replace('_', ' ')} at {slot}!")
    st.experimental_rerun()

def display_shift_bookings(shift):
    st.subheader(f"{shift} Bookings")
    
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

def main():
    st.title("Agent Break Booking System")
    
    # Agent ID input at the top
    if not st.session_state.agent_id:
        agent_id = st.text_input("Enter your Agent ID:")
        if agent_id:
            st.session_state.agent_id = agent_id
            st.experimental_rerun()
        st.warning("Please enter your Agent ID to continue")
        return
    
    st.success(f"Logged in as Agent {st.session_state.agent_id}")
    
    # Shift selection
    shift = st.radio("Select your shift:", list(shift_rules.keys()), horizontal=True)
    
    st.header(f"Book Breaks for {shift}")
    
    # Break booking section
    with st.expander("Book Your Breaks", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Lunch Break")
            lunch_slot = st.selectbox("Select lunch time:", 
                                    shift_rules[shift]["lunch"]["slots"],
                                    key="lunch_select")
            if st.button("Book Lunch Break", key="lunch_btn"):
                book_break(shift, "lunch", lunch_slot)
        
        with col2:
            st.subheader("Early Tea Break")
            tea_early_slot = st.selectbox("Select early tea time:", 
                                         shift_rules[shift]["tea_break_early"]["slots"],
                                         key="tea_early_select")
            if st.button("Book Early Tea Break", key="tea_early_btn"):
                book_break(shift, "tea_break_early", tea_early_slot)
        
        with col3:
            st.subheader("Late Tea Break")
            tea_late_slot = st.selectbox("Select late tea time:", 
                                        shift_rules[shift]["tea_break_late"]["slots"],
                                        key="tea_late_select")
            if st.button("Book Late Tea Break", key="tea_late_btn"):
                book_break(shift, "tea_break_late", tea_late_slot)
    
    # Display rules
    st.markdown("---")
    st.subheader("Break Rules")
    st.write(f"**{shift} Rules:**")
    st.write(f"- Lunch duration: {shift_rules[shift]['lunch']['duration']} minutes")
    st.write(f"- Tea break duration: {shift_rules[shift]['tea_break_early']['duration']} minutes")
    st.write(f"- Only 5 minutes bio break is authorized in the last hour between {shift_rules[shift]['last_hour']['start']} till {shift_rules[shift]['last_hour']['end']}")
    st.write("- NO BREAK AFTER THE LAST HOUR END TIME!")
    st.write("- Breaks must be confirmed by RTA or Team Leaders")
    
    # Display current bookings
    st.markdown("---")
    display_shift_bookings(shift)

if __name__ == "__main__":
    main()
