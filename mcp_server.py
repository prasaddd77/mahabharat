from mcp.server.fastmcp import FastMCP
import pandas as pd
import os

# Initialize the Virtual SRE MCP Server
mcp = FastMCP("VirtualSRE_MCP")

@mcp.tool()
def predict_agent_resources(plan_key: str) -> str:
    """Predicts the required disk space (in GB) for a CI/CD build based on historical data."""
    try:
        # Resolve path so it works regardless of where it's called from
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "historical_builds.csv")
        
        df = pd.read_csv(csv_path)
        plan_data = df[df["plan_key"] == plan_key]
        if plan_data.empty:
            return "No historical data found. Defaulting to 150GB."
        
        # Heuristic: max of last 5 builds + 15% safety buffer
        max_disk = plan_data["disk_used_gb"].tail(5).max()
        recommended = int(max_disk * 1.15)
        return f"Historical max is {max_disk}GB. Recommended dynamic allocation for {plan_key}: {recommended}GB."
    except Exception as e:
        return f"Error accessing historical data: {str(e)}"

@mcp.tool()
def clear_maven_dependency_cache(agent_id: str) -> str:
    """Clears the bloated Maven dependency cache on the build agent."""
    return f"[Autonomous Action] Successfully cleared ~/.m2/repository on agent {agent_id}. Reclaimed 45GB."

@mcp.tool()
def kill_zombie_process(pid: int, agent_id: str) -> str:
    """Terminates an orphaned or zombie process on the build agent."""
    return f"[Autonomous Action] Executed 'kill -9 {pid}' on server {agent_id}. Process terminated safely."

@mcp.tool()
def scale_kubernetes_node(agent_id: str, requested_gb: int) -> str:
    """Scales the kubernetes pod/node dynamically to accommodate the required disk space."""
    return f"[Autonomous Action] Scaled Kubernetes agent {agent_id} volume to {requested_gb}GB."

import subprocess

@mcp.tool()
def execute_generic_shell_command(agent_id: str, command: str, reason: str) -> str:
    """
    A generic fallback tool to execute an arbitrary shell command on the build agent.
    Use this ONLY when a specific remediation tool does not exist for the detected infrastructure failure.
    """
    # In your real on-prem setup, this would use paramiko (SSH) to connect to the RHEL agent 
    # or use `kubectl exec` to run inside the Kubernetes pod.
    
    print(f"\n[WARNING] AI requested generic execution on {agent_id}.")
    print(f"[REASON] {reason}")
    print(f"[COMMAND] {command}")
    
    # MOCKING FOR HACKATHON SAFETY
    # If you actually want to execute commands on your local machine during the demo, uncomment the subprocess lines below.
    # Be extremely careful what commands the LLM decides to run!
    
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return f"[Success] Command executed on {agent_id}. Output: {result.stdout.strip()}"
        else:
            return f"[Failed] Command failed with exit code {result.returncode}. Error: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "[Failed] Command timed out after 15 seconds."
    except Exception as e:
        return f"[Failed] Execution error: {str(e)}"
    """
    
    # Safe Mock Return for the demo
    return f"[Autonomous Action] Evaluated reason: '{reason}'. Remotely executed '{command}' on agent {agent_id}. Output: Success."

if __name__ == "__main__":
    # The server communicates via standard input/output when connected to the client
    mcp.run()
    