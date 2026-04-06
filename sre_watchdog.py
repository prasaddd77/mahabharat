import time
import json
import os
import subprocess
import requests
from datetime import datetime
import sys
# --- CONFIGURATION ---
JENKINS_URL = "http://localhost:8080"
JENKINS_USER = "root" # Update this
JENKINS_TOKEN = "1150869c09c1d91f816929a36f3daa7cf6"  # Update this
AUTH = (JENKINS_USER, JENKINS_TOKEN)

# We use this file so the AI remembers which builds it already fixed
STATE_FILE = "processed_builds.json"
REPORTS_DIR = "sre_reports"

os.makedirs(REPORTS_DIR, exist_ok=True)

def load_processed_builds():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_processed_builds(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_all_jobs():
    try:
        response = requests.get(f"{JENKINS_URL}/api/json?tree=jobs[name]", auth=AUTH)
        response.raise_for_status()
        return [job['name'] for job in response.json().get('jobs', [])]
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []

def check_for_failures():
    processed_builds = load_processed_builds()
    jobs = get_all_jobs()
    for job in jobs:
        try:
            # Check the status of the latest build
            job_url = f"{JENKINS_URL}/job/{job}/api/json"
            response = requests.get(job_url, auth=AUTH)
            response.raise_for_status()
            last_build = response.json().get('lastBuild')
            if not last_build:
                continue
            build_num = str(last_build['number'])
            # Check if we already processed this exact build
            if job in processed_builds and processed_builds[job] == build_num:
                continue

            # Fetch build details to see if it failed
            build_url = f"{JENKINS_URL}/job/{job}/{build_num}/api/json"
            build_resp = requests.get(build_url, auth=AUTH)
            build_resp.raise_for_status()
            build_result = build_resp.json().get('result')

            # TRIGGER CONDITION: If it FAILED, run the Virtual SRE
            if build_result == "FAILURE":
                print(f"\n🚨 [WATCHDOG] Detected new failure on {job} (Build #{build_num}). Triggering AI...")
                # Fetch the raw log
                log_url = f"{JENKINS_URL}/job/{job}/{build_num}/consoleText"
                log_resp = requests.get(log_url, auth=AUTH)
                raw_log = log_resp.text
                # Save log temporarily for the AI to read
                temp_log = f"temp_{job}_log.txt"
                with open(temp_log, "w", encoding="utf-8") as f:
                    f.write(raw_log)
                # Run the Virtual SRE Engine
                script_path = os.path.join(os.path.dirname(__file__), "virtual_sre.py")
                result = subprocess.run(["python3", script_path, temp_log], capture_output=True, text=True)
                # result = subprocess.run([sys.executable, script_path, temp_log], capture_output=False)
                # # Because we are printing live, we read the final saved file to pass to the dashboard
                # if os.path.exists("sre_reports/latest_run.txt"):
                #     pass # The dashboard will read from the reports folder
                # Save the AI's report for the dashboard to read
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = os.path.join(REPORTS_DIR, f"{timestamp}_{job}.txt")
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)
                print(f"✅ [WATCHDOG] SRE Remediation complete for {job}. Report saved.")
                # Mark as processed so we don't loop infinitely
                processed_builds[job] = build_num
                save_processed_builds(processed_builds)
                # Clean up temp file
                if os.path.exists(temp_log): os.remove(temp_log)

        except Exception as e:
            print(f"Error checking job {job}: {e}")

if __name__ == "__main__":
    print("========================================")
    print("👁️ Virtual SRE Watchdog Daemon Started 👁️")
    print("Polling Jenkins every 10 seconds...")
    print("========================================")
    while True:
        check_for_failures()
        time.sleep(10) # Wait 10 seconds before polling again