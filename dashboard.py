import streamlit as st

# Read log file
with open("pipeline_logs.txt","r") as f:
    logs = f.read().splitlines()

# Count ERROR lines
error_lines = [line for line in logs if "[ERROR]" in line]
total_errors = len(error_lines)

st.title("Self-Healing Pipeline Dashboard")
st.metric("Total Errors Detected", total_errors)

st.subheader("Error Logs")
st.text("\n".join(error_lines))