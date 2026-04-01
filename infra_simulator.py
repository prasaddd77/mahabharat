import os
import time
import subprocess
import sys
import psutil

# Define our mock agent paths
BASE_DIR = os.path.join(os.getcwd(), "mock_agent_workspace")
MAVEN_CACHE = os.path.join(BASE_DIR, ".m2", "repository")
OLD_WORKSPACES = os.path.join(BASE_DIR, "xml-data", "build-dir")

def create_junk_files(directory, num_files, size_mb):
    """Creates actual physical files to simulate disk bloat."""
    os.makedirs(directory, exist_ok=True)
    for i in range(num_files):
        file_path = os.path.join(directory, f"bloated_cache_file_{i}.dat")
        # Write random bytes to create a real file of specified size
        with open(file_path, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))

def spawn_zombie_process():
    """Spawns a real background Python process that does nothing (a zombie)."""
    # Spawns a background process that just sleeps for an hour
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])
    return p.pid

if __name__ == "__main__":
    print("🧹 [1/3] Cleaning up old simulation data...")
    if os.path.exists(BASE_DIR):
        import shutil
        shutil.rmtree(BASE_DIR)

    print("🏗️ [2/3] Generating bloated Maven & Workspace directories (creating ~200MB of junk)...")
    create_junk_files(MAVEN_CACHE, num_files=10, size_mb=10) # 100MB
    create_junk_files(OLD_WORKSPACES, num_files=5, size_mb=20) # 100MB

    print("🧟 [3/3] Spawning 'zombie' build processes...")
    pid1 = spawn_zombie_process()
    pid2 = spawn_zombie_process()
    
    # Save PIDs so the MCP server can find them
    with open("zombie_pids.txt", "w") as f:
        f.write(f"{pid1}\n{pid2}")

    print("======================================================")
    print("✅ Local Agent Simulator is bloated and ready!")
    print(f"📁 Check your file explorer: {BASE_DIR}")
    print(f"⚙️  Zombie PIDs running in background: {pid1}, {pid2}")
    print("======================================================")