import requests
import base64

JENKINS_URL = "http://localhost:8080"
JENKINS_USER = "root" # e.g., "admin"
JENKINS_TOKEN = "1150869c09c1d91f816929a36f3daa7cf6"  # The token you just generated
AUTH = (JENKINS_USER, JENKINS_TOKEN)

def get_all_jenkins_jobs():
    """Fetches a list of all pipeline names currently in Jenkins."""
    try:
        url = f"{JENKINS_URL}/api/json?tree=jobs[name]"
        response = requests.get(url, auth=AUTH)
        response.raise_for_status()

        jobs = [job['name'] for job in response.json().get('jobs', [])]
        return jobs if jobs else ["No jobs found"]
    except Exception as e:
        print(f"Connection Error: {str(e)}")
        return []

def get_latest_log_for_job(job_name: str) -> str:
    """Fetches the raw console output of the latest build for a specific job."""
    try:
        # Get latest build number
        job_url = f"{JENKINS_URL}/job/{job_name}/api/json"
        response = requests.get(job_url, auth=AUTH)
        response.raise_for_status()

        last_build = response.json().get('lastBuild')
        if not last_build:
            return f"No builds have been run yet for {job_name}."

        latest_build_number = last_build['number']

        # Get the log
        log_url = f"{JENKINS_URL}/job/{job_name}/{latest_build_number}/consoleText"
        log_response = requests.get(log_url, auth=AUTH)
        log_response.raise_for_status()

        return log_response.text
    except Exception as e:
        return f"CRITICAL_CONNECTION_ERROR: {str(e)}"