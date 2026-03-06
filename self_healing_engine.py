def cleanup_disk():
    print("Simulated: Cleaning disk space...")

def restart_agent():
    print("Simulated: Restarting build agent...")

def scale_agents():
    print("Simulated: Scaling build agents...")

def auto_fix(log_analysis):
    log_analysis = log_analysis.lower()
    if "disk" in log_analysis:
        cleanup_disk()
    elif "zombie" in log_analysis:
        restart_agent()
    else:
        scale_agents()

if __name__ == "__main__":
    issue = input("Enter detected issue (or paste AI analysis): ")
    auto_fix(issue)