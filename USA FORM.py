import streamlit as st

# Set the title of the page (optional)
st.title("Status Update")

# Display the message
st.markdown(
    """
    <div style='text-align: center; font-size: 24px; color: red; margin-top: 50px;'>
        <strong>Not Available</strong><br>
        <span style='font-size: 20px; color: gray;'>Waiting for management approval</span>
    </div>
    """,
    unsafe_allow_html=True
)
