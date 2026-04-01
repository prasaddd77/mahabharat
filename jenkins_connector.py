import requests
import base64

JENKINS_URL = "http://localhost:8080"
JENKINS_USER = "root" # e.g., "admin"
JENKINS_TOKEN = "1150869c09c1d91f816929a36f3daa7cf6"  # The token you just generated

def get_latest_failed_log(job_name: str) -> str:
    """Fetches the raw console output of the latest failed Jenkins build."""
    try:
        # 1. Get the latest build number
        job_url = f"{JENKINS_URL}/job/{job_name}/api/json"
        auth = (JENKINS_USER, JENKINS_TOKEN)
        
        response = requests.get(job_url, auth=auth)
        response.raise_for_status()
        latest_build_number = response.json()['lastBuild']['number']
        
        # 2. Get the raw console log for that build
        log_url = f"{JENKINS_URL}/job/{job_name}/{latest_build_number}/consoleText"
        log_response = requests.get(log_url, auth=auth)
        log_response.raise_for_status()
        
        return log_response.text
    except Exception as e:
        return f"Error connecting to local Jenkins: {str(e)}"

# Quick test if you run this script directly
if __name__ == "__main__":
    log = get_latest_failed_log("Billing-Service-Core")
    print(log[:500] + "...\n[Log truncated for preview]")