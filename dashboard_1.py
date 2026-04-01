import streamlit as st
import subprocess
import os
import re
import json

st.set_page_config(page_title="Virtual SRE Dashboard", layout="wide")

st.title("🛠️ DevOps: Virtual SRE Engine")
st.markdown("Transforming Kubernetes pipelines from fragile to self-healing using AI and MCP.")

# Create a mock list of failed pipelines
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Failed Pipelines Queue")
    selected_log = st.radio(
        "Select Pipeline to Analyze:",
        ["pipeline_logs.txt", "dual_failure_logs.txt", "queued_pipelines.txt"]
    )
    
    # Map selection to actual file
    log_file_map = {
        "pipeline_logs.txt": "pipeline_logs_1.txt",
        "dual_failure_logs.txt": "dual_failure_logs.txt",
        "queued_pipelines.txt": "queued_pipelines.txt"
    }
    target_file = log_file_map[selected_log]

    plan_key = "billing-service"
    agent_id = "sbcm-prod-ci-d71dz"
    
    if st.button("Trigger Virtual SRE Auto-Remediation", type="primary"):
        with st.spinner(f"AI Analyzing {target_file}..."):
            # Run the virtual_sre.py script and capture output
            script_path = os.path.join(os.path.dirname(__file__), "virtual_sre.py")
            log_path = os.path.join(os.path.dirname(__file__), "test_logs", target_file)
            
            # Execute as a subprocess to capture terminal output for the dashboard
            env = os.environ.copy()
            result = subprocess.run(
                ["python", script_path, log_path],
                capture_output=True,
                text=True,
                env=env
            )
            # ... inside your dashboard.py after result = subprocess.run(...) ...
            st.session_state.run_result = result.stdout
            

            # Extract the JSON block for the UI metrics
            json_match = re.search(r'```json\n(.*?)\n```', result.stdout, re.DOTALL)
            if json_match:
                try:
                    metrics = json.loads(json_match.group(1))
                    
                    # Display the Operational Intelligence Dashboard
                    st.subheader("📊 Operational Intelligence Metrics")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Pipeline Health Score", f"{metrics.get('health_score', 0)}/100")
                    m2.metric("DevOps Hours Reclaimed", f"{metrics.get('reclaimed_hours', 0)} hrs")
                    m3.metric("Compute Costs Saved", f"${metrics.get('saved_compute_costs_usd', 0)}")
                    
                    st.info(f"**Bottleneck Insight:** {metrics.get('bottleneck_insight', 'N/A')}")
                    st.success(f"**Autonomous Actions Taken:** {metrics.get('autonomous_actions_taken', 'N/A')}")
                    
                except json.JSONDecodeError:
                    pass
                    if result.stderr:
                        st.session_state.run_result += f"\nERRORS:\n{result.stderr}"

with col2:
    st.subheader("SRE Engine Output")
    if "run_result" in st.session_state:
        st.code(st.session_state.run_result, language="log")
    else:
        st.info("Select a pipeline and click Trigger to see autonomous self-healing in action.")