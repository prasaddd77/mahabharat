import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

import re

async def analyze_and_heal(log_file_path: str):
    # Ensure API key is present
    # if not os.getenv("GEMINI_API_KEY"):
    #     print("ERROR: GEMINI_API_KEY environment variable not set.")
    #     sys.exit(1)

    client = genai.Client(api_key="YOUR_GEMINI_API_KEY_HERE")
    
    # Path to the MCP server script
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
    
    # Configure connection to the local MCP server
    server_params = StdioServerParameters(
        command="python",
        args=[server_script]
    )
    
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            logs = f.read()
    except FileNotFoundError:
        print(f"ERROR: Could not find log file at {log_file_path}")
        sys.exit(1)
    
    # --- DYNAMIC METADATA EXTRACTION ---
    metadata = extract_bamboo_metadata(logs)
    plan_name = metadata["plan_name"]
    plan_key = metadata["plan_key"]
    agent_id = metadata["agent_id"]

    print(f"[*] Connecting to Virtual SRE MCP Server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print(f"[*] Connected. Analyzing logs for: {plan_key}...\n")
            
            # Define the tools exactly as they are in the MCP server for Gemini to understand
            virtual_sre_tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name="predict_agent_resources",
                            description="Predicts required disk space (in GB) for a build based on historical data.",
                            parameters=types.Schema(type=types.Type.OBJECT, properties={"plan_key": types.Schema(type=types.Type.STRING)})
                        ),
                        types.FunctionDeclaration(
                            name="clear_maven_dependency_cache",
                            description="Clears the bloated Maven dependency cache on the build agent.",
                            parameters=types.Schema(type=types.Type.OBJECT, properties={"agent_id": types.Schema(type=types.Type.STRING)})
                        ),
                        types.FunctionDeclaration(
                            name="kill_zombie_process",
                            description="Terminates a hanging process on the build agent.",
                            parameters=types.Schema(type=types.Type.OBJECT, properties={
                                "pid": types.Schema(type=types.Type.INTEGER),
                                "agent_id": types.Schema(type=types.Type.STRING)
                            })
                        ),
                        types.FunctionDeclaration(
                            name="scale_kubernetes_node",
                            description="Scales the kubernetes pod dynamically to accommodate the required disk space.",
                            parameters=types.Schema(type=types.Type.OBJECT, properties={
                                "agent_id": types.Schema(type=types.Type.STRING),
                                "requested_gb": types.Schema(type=types.Type.INTEGER)
                            })
                        ),
                        types.FunctionDeclaration(
                            name="execute_generic_shell_command",
                            description="A fallback tool to execute an arbitrary bash/shell command on the build agent. Use this to run diagnostics (e.g., netstat, df, top) or apply custom fixes (e.g., rm, chmod, systemctl restart) when no specific tool exists.",
                            parameters=types.Schema(
                                type=types.Type.OBJECT, 
                                properties={
                                    "agent_id": types.Schema(type=types.Type.STRING),
                                    "command": types.Schema(type=types.Type.STRING, description="The exact bash command to execute."),
                                    "reason": types.Schema(type=types.Type.STRING, description="Brief explanation of why this command is being run.")
                                }
                            )
                        )
                    ]
                )
            ]
            
            prompt = f"""You are an autonomous Virtual SRE for our Kubernetes CI/CD pipelines.
            Plan Key: {plan_key}
            Agent Host: {agent_id}
            
            Instructions:
            1. Analyze the raw pipeline logs below to find the root cause of the failure.
            2. If the failure is infrastructure-related (e.g., out of disk space, zombie process), CALL THE APPROPRIATE TOOL to fix it. If it is disk space, first predict the resources needed, then scale the node.
            3. If it is an infrastructure issue but NO SPECIFIC TOOL EXISTS (e.g., network port binding, weird file permissions), use `execute_generic_shell_command` to write and execute a custom bash fix.
            4. If it is a code/compilation error, do not call tools. Instead, output a direct remediation summary for the developers.
            
            
            RAW LOGS:
            {logs}
            """
            
            # Request content from Gemini
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=virtual_sre_tools,
                    temperature=0.1
                )
            )
            
            print("================ AI ANALYSIS & ACTION ================")
            
            # Check if Gemini decided to invoke a tool
            if response.function_calls:
                for tool_call in response.function_calls:
                    print(f"\n[!] AI Triggered Tool: {tool_call.name}")
                    print(f"[!] Arguments: {tool_call.args}")
                    
                    # Execute the tool via the MCP server
                    result = await session.call_tool(tool_call.name, tool_call.args)
                    print(f"[>] MCP Server Result: {result.content[0].text}")
                    
            # Print the text response (often contains explanations or developer advice)
            if response.text:
                print(f"\n[AI Summary]:\n{response.text}")
            print("\n======================================================")


def extract_bamboo_metadata(log_text: str):
    """Parses raw Bamboo logs to dynamically extract the Plan details and Agent ID."""
    
    metadata = {
        "plan_name": "Unknown Plan",
        "plan_key": "UNKNOWN-KEY",
        "agent_id": "unknown-agent"
    }
    
    # Regex patterns specifically for Bamboo logs
    # Matches: Build [Plan Name] #128 ([PLAN-KEY-128]) is being prepared for building on agent [agent-id]
    prepare_pattern = r"Build (.*?) #\d+ \((.*?)-\d+\) is being prepared for building on agent ([\w-]+)"
    
    # Alternative match for just the host: Remote agent on host [agent-id]
    host_pattern = r"Remote agent on host ([\w-]+)"

    # Look through the first 20 lines to find the metadata quickly
    for line in log_text.splitlines()[:20]:
        
        # Try to match the massive first "prepared for building" line
        prepare_match = re.search(prepare_pattern, line)
        if prepare_match:
            # We strip out the " - default" or branch name suffix if it exists
            raw_name = prepare_match.group(1).replace(" - default", "").strip()
            
            metadata["plan_name"] = raw_name
            metadata["plan_key"] = prepare_match.group(2) # e.g., NGOFT-ZK8NGOFE1-JOB1
            metadata["agent_id"] = prepare_match.group(3) # e.g., eit-esom-ci-tykb9
            break # We found everything, stop searching
            
        # Fallback just in case we only find the host line
        host_match = re.search(host_pattern, line)
        if host_match and metadata["agent_id"] == "unknown-agent":
            metadata["agent_id"] = host_match.group(1)

    return metadata


if __name__ == "__main__":
    # You can pass arguments from command line or hardcode them for the demo
    # log_path = sys.argv[1] if len(sys.argv) > 1 else "test_logs/pipeline_logs.txt"
    # plan = sys.argv[2] if len(sys.argv) > 2 else "billing-service"
    # agent = sys.argv[3] if len(sys.argv) > 3 else "sbcm-prod-ci-d71dz"

    # asyncio.run(analyze_and_heal(log_path, plan, agent))
    
    # We now only need to pass the log file path, the script handles the rest!
    log_path = sys.argv[1] if len(sys.argv) > 1 else "test_logs/pipeline_logs.txt"
    
    asyncio.run(analyze_and_heal(log_path))
