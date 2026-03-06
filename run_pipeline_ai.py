from ai_analyzer import analyze_logs
from self_healing_engine import auto_fix

# Step 1: Analyze logs from text file
analysis = analyze_logs("pipeline_logs.txt")

print("\nAI Analysis:\n")
print(analysis)

# Step 2: Trigger simulated self-healing actions
print("\n===== SELF HEALING ACTION =====\n")
auto_fix(analysis)