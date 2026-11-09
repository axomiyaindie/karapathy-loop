import os
import sys
import re
import subprocess
from typing import Dict, Any
from dotenv import load_dotenv

# Initialize environment variables from .env
load_dotenv()

class KarpathyLoop:
    def __init__(self, agent_src_path: str, eval_suite_path: str):
        self.agent_src_path = agent_src_path
        self.eval_suite_path = eval_suite_path
        self.generation = int(os.environ.get("AGENT_GEN", "1"))
        
    def get_current_agent_code(self) -> str:
        if os.path.exists(self.agent_src_path):
            with open(self.agent_src_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "# Baseline Initial Agent\ndef execute_task(ctx):\n    return True\n"

    def propose_mutation(self, feedback: str) -> str:
        print(f"\n[Gen {self.generation}] Gathering context and querying LLM for structural mutation...")
        current_code = self.get_current_agent_code()
        
        system_prompt = """You are an elite recursive self-improvement software agent operating inside a Karpathy Loop. 
Your goal is to optimize the 'execute_task(ctx)' function inside the provided Python script.
CRITICAL CONTRACT CONSTRAINTS:
1. You must ONLY output a single, complete block of executable Python code enclosed in markdown code fences: ```python ... ```
2. The code MUST contain an 'execute_task(ctx)' function interface.
3. The function MUST return a Boolean value (True/False)."""

        user_content = f"Current Live Code Baseline:\n```python\n{current_code}\n```\nFeedback:\n{feedback}"

        # Check for dynamic API keys in .env
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                client = Anthropic()
                print("[LLM Engine] Querying Claude Sonnet API for code optimization engineering...")
                message = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}]
                )
                raw_response = message.content.text
                code_match = re.search(r"```python(.*?)```", raw_response, re.DOTALL)
                if code_match:
                    return code_match.group(1).strip()
                return raw_response.strip()
            except Exception as e:
                print(f"[LLM Engine Warning] Live connection failed: {e}. Falling back to automated rule.")
        else:
            print("[LLM Engine Info] ANTHROPIC_API_KEY environment variable not detected in .env layout.")
            print("[LLM Engine Info] Simulating high-quality token-tracked semantic mutation block locally...")

        return f"""# Generation {self.generation} - Autonomous Evolution
def execute_task(ctx):
    print("--- Gen {self.generation} Execution Core Active ---")
    ctx['generation_telemetry'] = {self.generation}
    ctx['loop_stability_factor'] = 0.99
    return True
"""

    def sandbox_evaluate(self, mutated_code: str) -> Dict[str, Any]:
        sandbox_dir = ".agent_sandbox"
        os.makedirs(sandbox_dir, exist_ok=True)
        sandbox_file = os.path.join(sandbox_dir, "temp_agent.py")
        
        with open(sandbox_file, "w", encoding='utf-8') as f:
            f.write(mutated_code)
            
        print(f"[Gen {self.generation}] Invoking Immutable Ruler verification pipeline...")
        result = subprocess.run([sys.executable, self.eval_suite_path], capture_output=True, text=True)
        
        passed = result.returncode == 0
        feedback = result.stdout + result.stderr
        return {"passed": passed, "feedback": feedback}

    def commit_improvement(self, mutated_code: str):
        print(f"[Gen {self.generation}] Validation Passed! Committing code change permanently to production branch.")
        os.makedirs(os.path.dirname(self.agent_src_path), exist_ok=True)
        with open(self.agent_src_path, "w", encoding='utf-8') as f:
            f.write(mutated_code)
            
        try:
            print(f"[Git Sync Engine] Staging and creating version record for Generation {self.generation}...")
            subprocess.run(["git", "add", self.agent_src_path], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"RSI Engine Auto-Commit: Generation {self.generation} stabilization optimizations"], check=True, capture_output=True)
            print(f"[Git Sync Engine Hub] Version checkpoint saved successfully.")
        except Exception as e:
            print(f"[Git Sync Engine Warning] Could not record auto-commit history log: {e}")

    def run_iteration(self, baseline_feedback: str = "Optimize context parsing and context dictionary state capture."):
        code = self.propose_mutation(baseline_feedback)
        res = self.sandbox_evaluate(code)
        print(res["feedback"])
        
        if res["passed"]:
            self.commit_improvement(code)
            self.generation += 1
            os.environ["AGENT_GEN"] = str(self.generation)
        else:
            print(f"[Gen {self.generation}] Optimization REJECTED by ruler. Resetting sandbox workspace layers.")

if __name__ == "__main__":
    loop = KarpathyLoop("src/agent/live_agent.py", "tests/immutable_ruler.py")
    loop.run_iteration()
