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

    client = genai.Client(api_key="")
    
    # Path to the MCP server script
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
    
    # Configure connection to the local MCP server
    server_params = StdioServerParameters(
        command="python3",
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
                            name="check_agent_disk_space",
                            description="Checks the real-time total, used, and free disk space of the specified build agent in MB. Call this before predicting resources.",
                            parameters=types.Schema(
                                type=types.Type.OBJECT, 
                                properties={"agent_id": types.Schema(type=types.Type.STRING)}
                            )
                        ),
                        types.FunctionDeclaration(
                            name="clean_bamboo_workspaces",
                            description="Deletes stale Bamboo workspaces from the OS to free up disk space. Use this if the expected footprint exceeds free space.",
                            parameters=types.Schema(
                                type=types.Type.OBJECT, 
                                properties={"agent_id": types.Schema(type=types.Type.STRING)}
                            )
                        ),
                        types.FunctionDeclaration(
                            name="cleanup_docker_volumes",
                            description="Preemptively sanitizes the agent by removing orphaned Docker volumes older than 10 days.",
                            parameters=types.Schema(
                                type=types.Type.OBJECT, 
                                properties={"agent_id": types.Schema(type=types.Type.STRING)}
                            )
                        ),
                        types.FunctionDeclaration(
                            name="predict_agent_resources",
                            description="Predicts required disk space (in MB) for a build based on historical data.",
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
                                "requested_mb": types.Schema(type=types.Type.INTEGER)
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
            
            prompt = f"""You are an autonomous "Virtual SRE" and AI-native CI/CD orchestration engine.
            Your objective is to transform our static Kubernetes Bamboo pipelines from a fragile process into a resilient, predictive, and self-healing utility.

            PIPELINE CONTEXT:
            Plan Key: {plan_key}
            Plan Name: {plan_name}
            Agent Host: {agent_id}
            
            RAW LOGS/EVENTS:
            {logs}

            Execute your analysis based on the type of input provided:

            SCENARIO A: PRE-FLIGHT CHECK (If the logs show a "BATCH QUEUE EVENT")
            1. Call `check_agent_disk_space` to get the target agent's current Free Space.
            2. Call `predict_agent_resources` for EVERY plan listed in the queue to get their expected footprints (in MB).
            3. Sum the footprints to get the Cumulative Required Space.
            4. Compare Cumulative Required Space to Free Space. 
            5. If Required > Free Space, you MUST preemptively call `clear_maven_dependency_cache` and `clean_bamboo_workspaces` to free up space. 
            6. After cleaning, verify the infrastructure is safe for the dispatcher to proceed.
            
            SCENARIO B: POST-MORTEM HEALING (If the logs show [ERROR] or [WARNING] failures)
            Execute your analysis and autonomous actions strictly across these four operational pillars:

            1. PREDICTIVE RESOURCE ORCHESTRATION (Dynamic Right-Sizing)
               - Call `check_agent_disk_space` to establish the current node baseline.
               - Call `predict_agent_resources` to determine the exact memory/disk footprint this specific pipeline requires based on historical data.
               - If the predicted footprint exceeds the current baseline, autonomously call `scale_kubernetes_node` to preemptively right-size the agent and prevent "Out-of-Disk" or OOM failures.

            2. INTELLIGENT SELF-HEALING (Auto-Remediation)
               - Deeply analyze the RAW LOGS to identify the root cause of the failure.
               - If you detect "Reactive Infrastructure Friction" (e.g., zombie processes, No space left on device, bloated Maven caches), autonomously trigger the appropriate cleanup tool WITHOUT requiring a human ticket.
               - If no specific tool exists for the infrastructure issue, use `execute_generic_shell_command` to apply a safe bash fix.
               - If the failure is a Code/Compilation issue, DO NOT call infrastructure tools. Output a direct developer remediation guide.

            3. PERFORMANCE BOTTLENECK DISCOVERY
               - Analyze the timestamps and step durations within the RAW LOGS.
               - Identify steps that cause long build queues (e.g., serialized testing, repetitive dependency downloads).
               - Provide explicit recommendations for Caching Optimizations and Step Parallelization to drastically reduce the "commit-to-deploy" lead time.

            4. OPERATIONAL INTELLIGENCE DASHBOARD
                - Calculate "health_score": Start at 100. Deduct 15 points if the build failed. Deduct 5 points for every WARNING found in the logs.
                - Calculate "reclaimed_hours": If you autonomously fixed an issue (like clearing cache or scaling), output 1.5 hours. If no action was taken, output 0.
                - Calculate "saved_compute_costs_usd": Multiply the predicted GB footprint by $0.03.

            RESPONSE FORMATTING:
            First, output your detailed SRE thought process, actions taken, root cause analysis, and bottleneck discovery. 
            
            Finally, you MUST end your response with a JSON block enclosed in ```json ... ``` containing the Operational Intelligence metrics so our dashboard can render them. Use this exact schema:
            ```json
            {{
              "health_score": 85,
              "reclaimed_hours": 1.5,
              "saved_compute_costs_usd": 12.50,
              "bottleneck_insight": "Short summary of parallelization/caching advice",
              "autonomous_actions_taken": "List of tools called or 'None'"
            }}
            ```
            """
            
            print("================ AI ANALYSIS & ACTION ================")
            
            # --- BULLETPROOF HACKATHON FIX: Manual Conversation History ---
            # We explicitly store the history so the AI remembers its previous tool calls
            conversation_history = [
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]

            for step in range(8): # Max 8 turns to prevent infinite loops
                # --- NEW RETRY LOGIC: Doesn't burn your steps! ---
                while True:
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=conversation_history,
                            config=types.GenerateContentConfig(
                                tools=virtual_sre_tools,
                                temperature=0.1
                            )
                        )
                        break # Success! Break out of the retry loop.
                    except Exception as e:
                        # Catch the 429 Rate Limit and pause instead of crashing
                        if "429" in str(e) or "quota" in str(e).lower() or "exhausted" in str(e).lower():
                            print(f"\n[!] Rate limit reached. SRE taking a 15-second breather...")
                            await asyncio.sleep(15)
                            #continue # Retries the exact same step!
                        else:
                            print(f"\n[ERROR] API crashed: {str(e)}")
                            sys.exit(1) # For unexpected errors, we exit to avoid undefined states
                    
                    # ... (rest of your tool execution code remains exactly the same) ...
                    
                    # # Add a tiny delay at the end of the loop to prevent burst limits
                    # await asyncio.sleep(2)
                
                if response.function_calls:
                    # 1. Add the AI's tool request to our history
                    conversation_history.append(response.candidates[0].content)
                    
                    tool_responses = []
                    for tool_call in response.function_calls:
                        print(f"\n[!] AI Triggered Tool: {tool_call.name}")
                        
                        # Safely extract arguments
                        args_dict = dict(tool_call.args) if hasattr(tool_call.args, 'keys') else tool_call.args
                        print(f"[!] Arguments: {args_dict}")
                        
                        try:
                            # Execute the tool via the MCP server
                            result = await session.call_tool(tool_call.name, args_dict)
                            tool_output = result.content[0].text
                        except Exception as e:
                            tool_output = f"Error executing tool: {str(e)}"
                            
                        print(f"[>] MCP Server Result: {tool_output}")
                        
                        # 2. Package the MCP result for Gemini
                        tool_responses.append(
                            types.Part.from_function_response(
                                name=tool_call.name,
                                response={"result": tool_output}
                            )
                        )
                    
                    # 3. Feed the MCP results back to Gemini as the next "user" message
                    conversation_history.append(
                        types.Content(role="user", parts=tool_responses)
                    )
                    
                    # Give the free tier a tiny pause between successful tool calls
                    await asyncio.sleep(2)
                    
                else:
                    # If no tools were called, the AI has formulated its final answer!
                    if response.text:
                        print(f"\n[AI Summary]:\n{response.text}")
                    break
                    
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
    log_path = sys.argv[1] if len(sys.argv) > 1 else "test_logs/pipeline_logs_1.txt"
    asyncio.run(analyze_and_heal(log_path))
