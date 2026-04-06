from mcp.server.fastmcp import FastMCP
import pandas as pd
import os
import subprocess
import hashlib  # <-- Missing import for the deterministic mapping
import shutil   # <-- Required for the check_agent_disk_space tool

# Initialize the Virtual SRE MCP Server
mcp = FastMCP("VirtualSRE_MCP")

@mcp.tool()
def check_agent_disk_space(agent_id: str, mount_path: str = "/") -> str:
    """Checks the real-time disk space of the agent."""
    try:
        # Check both directories Jenkins is bloating
        m2_path = os.path.expanduser("~/.m2/repository/junk")
        bamboo_path = os.path.expanduser("~/mock_bamboo_agent/xml-data/build-dir")
        
        total_size_bytes = 0
        for path in [m2_path, bamboo_path]:
            if os.path.exists(path):
                total_size_bytes += sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                       for dirpath, _, filenames in os.walk(path) 
                                       for filename in filenames)
        
        used_mb = total_size_bytes / (1024 * 1024)
        total_quota_mb = 250 # Our simulated agent maximum capacity
        free_mb = total_quota_mb - used_mb
        used_percentage = (used_mb / total_quota_mb) * 100
        
        return f"Agent {agent_id} Current State: Quota = {total_quota_mb}MB, Used = {used_mb:.1f}MB, Free = {free_mb:.1f}MB. Currently {used_percentage:.1f}% full."
    except Exception as e:
        return f"Failed to check disk space: {str(e)}"
    # """
    # Checks the real-time total and free disk space (in GB) of the specified build agent.
    # Use this to establish the current baseline before a batch of pipelines executes.
    # """
    # try:
    #     # For a local hackathon demo, this checks the local drive. 
    #     # In production, this would map to your specific RHEL mount points (e.g., "/opt/bamboo-agent")
    #     total, used, free = shutil.disk_usage(mount_path)
        
    #     total_gb = total // (2**30)
    #     free_gb = free // (2**30)
    #     used_percentage = (used / total) * 100
        
    #     return f"Agent {agent_id} Current State: Total Space = {total_gb}GB, Free Space = {free_gb}GB. Currently {used_percentage:.1f}% full."
    # except Exception as e:
    #     return f"Failed to check disk space on {agent_id}: {str(e)}"
    

@mcp.tool()
def predict_agent_resources(plan_key: str) -> str:
    """Predicts the required disk footprint (in MB) for a specific CI/CD build based on historical data."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "historical_builds.csv")
        df = pd.read_csv(csv_path)
        
        # Deterministic mapping
        unique_pipes = df["pipeline_id"].unique()
        numeric_hash = int(hashlib.md5(plan_key.encode('utf-8')).hexdigest(), 16)
        mapped_pipe_id = unique_pipes[numeric_hash % len(unique_pipes)]
        
        plan_data = df[df["pipeline_id"] == mapped_pipe_id]
        if plan_data.empty:
            return f"No historical data found for {plan_key}. Defaulting to 50MB."
        
        # Hackathon Scaling: Convert the Kaggle memory metric to an MB disk footprint
        # tailored specifically for our 250MB local OS simulator quota.
        max_metric = plan_data["memory_usage_mb"].tail(5).max()
        simulated_disk_mb = max(30, int(max_metric / 300)) # Will output ~70MB to 90MB per pipeline
        
        return f"Historical expected disk footprint for {plan_key} is {simulated_disk_mb}MB."
    except Exception as e:
        return f"Error accessing historical data: {str(e)}"
    # """
    # Predicts the required disk footprint (in GB) for a specific CI/CD build based on historical data.
    # Call this for EACH pipeline in the queue to calculate the cumulative expected footprint.
    # """
    # try:
    #     base_dir = os.path.dirname(os.path.abspath(__file__))
    #     csv_path = os.path.join(base_dir, "historical_builds.csv")
        
    #     df = pd.read_csv(csv_path)
        
    #     # Deterministically map the real Bamboo plan_key to a Kaggle pipeline_id
    #     unique_pipes = df["pipeline_id"].unique()
    #     numeric_hash = int(hashlib.md5(plan_key.encode('utf-8')).hexdigest(), 16)
    #     mapped_pipe_id = unique_pipes[numeric_hash % len(unique_pipes)]
        
    #     plan_data = df[df["pipeline_id"] == mapped_pipe_id]
        
    #     if plan_data.empty:
    #         return f"No historical data found for {plan_key}. Defaulting expected footprint to 5GB."
        
    #     # Hackathon Conversion: Since the Kaggle dataset uses memory_usage_mb, 
    #     # we mathematically simulate a disk footprint (GB) for the demo.
    #     # Example: 4000MB memory usage implies a heavy build, translating to roughly 8GB of disk I/O.
    #     max_metric = plan_data["memory_usage_mb"].tail(5).max()
    #     simulated_disk_gb = max(2, int((max_metric / 1024) * 2.5)) 
        
    #     return f"Historical expected disk footprint for {plan_key} is {simulated_disk_gb}GB."
    # except Exception as e:
    #     return f"Error accessing historical data: {str(e)}"

# @mcp.tool()
# def predict_agent_resources(plan_key: str) -> str:
#     """Predicts the required disk space (in GB) for a CI/CD build based on historical data."""
#     try:
#         # Resolve path so it works regardless of where it's called from
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         csv_path = os.path.join(base_dir, "historical_builds.csv")
        
#         df = pd.read_csv(csv_path)
#         plan_data = df[df["plan_key"] == plan_key]
#         if plan_data.empty:
#             return "No historical data found. Defaulting to 150GB."
        
#         # Heuristic: max of last 5 builds + 15% safety buffer
#         max_disk = plan_data["disk_used_gb"].tail(5).max()
#         recommended = int(max_disk * 1.15)
#         return f"Historical max is {max_disk}GB. Recommended dynamic allocation for {plan_key}: {recommended}GB."
#     except Exception as e:
#         return f"Error accessing historical data: {str(e)}"

# @mcp.tool()
# def predict_agent_resources(plan_key: str) -> str:
#     """Predicts the required memory (in MB) for a CI/CD build based on historical data."""
#     try:
#         # Resolve path so it works regardless of where it's called from
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         csv_path = os.path.join(base_dir, "historical_builds.csv")
        
#         df = pd.read_csv(csv_path)
        
#         # Match the LLM's plan_key to the new dataset's pipeline_id column
#         plan_data = df[df["pipeline_id"] == plan_key]
        
#         if plan_data.empty:
#             return "No historical data found. Defaulting to 4096MB (4GB)."
        
#         # Heuristic: max memory of last 5 builds + 15% safety buffer
#         max_memory = plan_data["memory_usage_mb"].tail(5).max()
#         recommended_mb = int(max_memory * 1.15)
        
#         return f"Historical max memory is {max_memory}MB. Recommended dynamic memory allocation for {plan_key}: {recommended_mb}MB."
#     except Exception as e:
#         return f"Error accessing historical data: {str(e)}"

@mcp.tool()
def cleanup_docker_volumes(agent_id: str) -> str:
    """
    Preemptively sanitizes the agent by removing orphaned Docker volumes older than 10 days.
    """
    # Hackathon Mock Execution
    print(f"\n[EXECUTION] Running 'docker system prune -a --volumes --filter \"until=240h\"' on {agent_id}...")
    
    # Simulate reclaiming space
    reclaimed_gb = 18 
    return f"[Autonomous Action] Successfully pruned old Docker volumes on {agent_id}. Reclaimed {reclaimed_gb}GB of disk space."

@mcp.tool()
def clear_maven_dependency_cache(agent_id: str) -> str:
    """Actually deletes the bloated Maven dependency cache directory from the OS."""
    #maven_path = os.path.join(os.getcwd(), "mock_agent_workspace", ".m2")
    maven_path = os.path.expanduser("~/.m2/repository/junk")
    if os.path.exists(maven_path):
        shutil.rmtree(maven_path) # Physically deletes the folder and files!
        return f"[Autonomous Action] Successfully purged Maven cache on {agent_id}. Disk space reclaimed instantly."
    return f"[Action Skipped] Maven cache not found on {agent_id}."
    # """
    # Clears the bloated Maven dependency cache (~/.m2/repository) on the build agent.
    # """
    # print(f"\n[EXECUTION] Running 'rm -rf ~/.m2/repository/com/internal/*' on {agent_id}...")
    # reclaimed_gb = 12
    # return f"[Autonomous Action] Successfully cleared Maven cache on {agent_id}. Reclaimed {reclaimed_gb}GB of disk space."

# @mcp.tool()
# def clear_maven_dependency_cache(agent_id: str) -> str:
#     """Clears the bloated Maven dependency cache on the build agent."""
#     return f"[Autonomous Action] Successfully cleared ~/.m2/repository on agent {agent_id}. Reclaimed 45GB."

@mcp.tool()
def clean_bamboo_workspaces(agent_id: str) -> str:
    """Actually deletes stale Bamboo workspaces from the OS to free up disk space."""
    workspace_path = os.path.expanduser("~/mock_bamboo_agent/xml-data/build-dir")
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path) # Physically deletes the mock workspaces
        return f"[Autonomous Action] Successfully purged stale Bamboo workspaces on {agent_id}."
    return f"[Action Skipped] No workspaces found to clean on {agent_id}."
    # """
    # Cleans up old Bamboo working directories, explicitly keeping directories tied to current active dependencies.
    # """
    # print(f"\n[EXECUTION] Cleaning /home/bamboo/bamboo-agent-home/xml-data/build-dir/ on {agent_id}...")
    # print(f"[PRESERVATION] Excluding active dependencies: {exclude_dependencies}")
    
    # reclaimed_gb = 25
    # return f"[Autonomous Action] Cleaned stale Bamboo workspaces on {agent_id}. Preserved {exclude_dependencies}. Reclaimed {reclaimed_gb}GB."

@mcp.tool()
def kill_zombie_process(pid: int, agent_id: str) -> str:
    # """Terminates an orphaned or zombie process on the build agent."""
    # return f"[Autonomous Action] Executed 'kill -9 {pid}' on server {agent_id}. Process terminated safely."
    """Reads the zombie PIDs and forcefully kills them using the OS."""
    try:
        if not os.path.exists("zombie_pids.txt"):
            return "No zombie processes found."
            
        with open("zombie_pids.txt", "r") as f:
            pids = f.read().splitlines()
            
        killed_list = []
        for pid_str in pids:
            pid = int(pid_str)
            if psutil.pid_exists(pid):
                p = psutil.Process(pid)
                p.terminate() # Physically kills the OS process!
                killed_list.append(str(pid))
                
        os.remove("zombie_pids.txt")
        return f"[Autonomous Action] Forcefully terminated zombie PIDs: {', '.join(killed_list)} on {agent_id}."
    except Exception as e:
        return f"Failed to kill processes: {str(e)}"

@mcp.tool()
def scale_kubernetes_node(agent_id: str, requested_mb: int) -> str:
    """Scales the kubernetes pod/node dynamically to accommodate the required disk space."""
    return f"[Autonomous Action] Scaled Kubernetes agent {agent_id} volume to {requested_mb}MB."

@mcp.tool()
def execute_generic_shell_command(agent_id: str, command: str, reason: str) -> str:
    """A fallback tool to execute an arbitrary bash command if a specific cleanup tool does not exist."""
    print(f"\n[WARNING] AI requested generic execution on {agent_id}.")
    print(f"[REASON] {reason}")
    print(f"[COMMAND] {command}")
    
    return f"[Autonomous Action] Evaluated reason: '{reason}'. Remotely executed '{command}' on agent {agent_id}. Output: Success."

# @mcp.tool()
# def execute_generic_shell_command(agent_id: str, command: str, reason: str) -> str:
#     """
#     A generic fallback tool to execute an arbitrary shell command on the build agent.
#     Use this ONLY when a specific remediation tool does not exist for the detected infrastructure failure.
#     """
#     # In your real on-prem setup, this would use paramiko (SSH) to connect to the RHEL agent 
#     # or use `kubectl exec` to run inside the Kubernetes pod.
    
#     print(f"\n[WARNING] AI requested generic execution on {agent_id}.")
#     print(f"[REASON] {reason}")
#     print(f"[COMMAND] {command}")
    
#     # MOCKING FOR HACKATHON SAFETY
#     # If you actually want to execute commands on your local machine during the demo, uncomment the subprocess lines below.
#     # Be extremely careful what commands the LLM decides to run!
    
#     """
#     try:
#         result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
#         if result.returncode == 0:
#             return f"[Success] Command executed on {agent_id}. Output: {result.stdout.strip()}"
#         else:
#             return f"[Failed] Command failed with exit code {result.returncode}. Error: {result.stderr.strip()}"
#     except subprocess.TimeoutExpired:
#         return "[Failed] Command timed out after 15 seconds."
#     except Exception as e:
#         return f"[Failed] Execution error: {str(e)}"
#     """
    
#     # Safe Mock Return for the demo
#     return f"[Autonomous Action] Evaluated reason: '{reason}'. Remotely executed '{command}' on agent {agent_id}. Output: Success."

if __name__ == "__main__":
    # The server communicates via standard input/output when connected to the client
    mcp.run()