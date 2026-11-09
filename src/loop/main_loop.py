import os
import sys
import re
import subprocess
from typing import Dict, Any
from dotenv import load_dotenv

# Ensure local custom imports function cleanly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from context.engine import ContextEngine

# Load runtime environment variables
load_dotenv()

class KarpathyLoop:
    def __init__(self, agent_src_path: str, eval_suite_path: str):
        self.agent_src_path = agent_src_path
        self.eval_suite_path = eval_suite_path
        self.generation = int(os.environ.get("AGENT_GEN", "1"))
        self.context_engine = ContextEngine(token_limit=3500)
        
    def get_current_agent_code(self) -> str:
        if os.path.exists(self.agent_src_path):
            with open(self.agent_src_path, 'r', encoding='utf-8') as f:
                return f.read()
        return "# Baseline Initial Agent\ndef execute_task(ctx):\n    return True\n"

    def query_live_llm(self, system_prompt: str, user_content: str) -> str:
        provider = os.environ.get("RSI_LLM_PROVIDER", "anthropic").lower()
        
        if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            from anthropic import Anthropic
            print("[LLM Engine] Querying Claude API for system optimizations...")
            client = Anthropic()
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return message.content.text
            
        elif provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            from openai import OpenAI
            print("[LLM Engine] Querying OpenAI GPT-4o API for system optimizations...")
            client = OpenAI()
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=2048
            )
            return completion.choices.message.content
        else:
            raise ValueError(f"Selected provider '{provider}' key or dependencies missing. Reverting to fallback.")

    def propose_mutation(self, feedback: str) -> str:
        print(f"\n[Gen {self.generation}] Assembling telemetry context and querying structural mutation...")
        current_code = self.get_current_agent_code()
        compressed_history = self.context_engine.compress_context()
        
        system_prompt = """You are an elite recursive self-improvement software agent operating inside a Karpathy Loop. 
Your goal is to optimize the 'execute_task(ctx)' function inside the provided Python script.
CRITICAL CONTRACT CONSTRAINTS:
1. You must ONLY output a single, complete block of executable Python code enclosed in markdown code fences: ```python ... ```
2. The code MUST contain an 'execute_task(ctx)' function interface.
3. The function MUST return a Boolean value (True/False)."""

        user_content = f"{compressed_history}\n\nCurrent Live Code Baseline:\n```python\n{current_code}\n```\n\nFeedback:\n{feedback}"

        try:
            raw_response = self.query_live_llm(system_prompt, user_content)
            code_match = re.search(r"```python(.*?)```", raw_response, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            return raw_response.strip()
        except Exception:
            print(f"[LLM Engine Info] Live compilation token not available. Running local simulation variant.")

        # Simulate a slight code structural break on Round 2 for testing rollback recovery workflows safely
        if self.generation == 2:
            return """# Generation 2 - Intentionally Broken Syntax Variant
def execute_task(ctx):
    print("--- Gen 2 Breaking Protocol ---"
    # Missing closing parenthesis above will trigger a parse syntax failure!
    return True
"""

        return f"""# Generation {self.generation} - Autonomous Evolution Path
def execute_task(ctx):
    print("--- Gen {self.generation} Active Engine Running ---")
    ctx['generation_telemetry'] = {self.generation}
    ctx['loop_stability_factor'] = 0.95 + ({self.generation} * 0.01)
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
        print(f"[Gen {self.generation}] Validation Passed! Committing code change permanently.")
        os.makedirs(os.path.dirname(self.agent_src_path), exist_ok=True)
        with open(self.agent_src_path, "w", encoding='utf-8') as f:
            f.write(mutated_code)
            
        try:
            print(f"[Git Sync Engine] Staging configuration changes...")
            subprocess.run(["git", "add", self.agent_src_path], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"RSI Engine Update: Generation {self.generation}"], check=True, capture_output=True)
            print(f"[Git Sync Engine Hub] Version record checkpoint finalized.")
            
            print(f"[Git Cloud Sync] Broadcasting Generation {self.generation} mutations to GitHub upstream...")
            subprocess.run(["git", "push", "origin", "main"], check=True, capture_output=True)
            print(f"[Git Cloud Sync] Cloud push sync completed successfully.")
        except Exception as e:
            print(f"[Git Sync Engine Warning] Could not finalize repository push: {e}")

    def handle_degeneration_rollback(self, failure_feedback: str):
        """
        NATIVE AUTONOMOUS ROLLBACK ENGINE
        If code verification breaks, perform a hard reset to return the 
        workspace files cleanly to the last stable Git commit checkpoint.
        """
        print(f"\n[CRITICAL ERROR] Gen {self.generation} validation broke the Immutable Ruler rubric!")
        print(f"[Rollback Engine] Initiating automated file-system recovery sequence...")
        try:
            # Revert any uncommitted modifications in the master agent script
            subprocess.run(["git", "checkout", "HEAD", "--", self.agent_src_path], check=True, capture_output=True)
            # Purge temp sandbox execution folders
            if os.path.exists(".agent_sandbox/temp_agent.py"):
                os.remove(".agent_sandbox/temp_agent.py")
            print("[Rollback Engine Hub] Git branch recovered cleanly to last known stable commit.")
        except Exception as e:
            print(f"[Rollback Engine Exception] System state recover crash: {e}")

    def run_iteration(self, baseline_feedback: str = "Optimize context parsing and memory structure capture."):
        self.context_engine.add_interaction("system", f"Initializing generation pass tracking {self.generation}")
        
        code = self.propose_mutation(baseline_feedback)
        res = self.sandbox_evaluate(code)
        print(res["feedback"])
        
        if res["passed"]:
            self.commit_improvement(code)
            self.context_engine.add_interaction("ruler", f"Generation {self.generation} verified cleanly.")
            self.generation += 1
            os.environ["AGENT_GEN"] = str(self.generation)
            return True
        else:
            self.context_engine.add_interaction("ruler", f"Generation {self.generation} failed validation: {res['feedback']}")
            self.handle_degeneration_rollback(res["feedback"])
            return False

if __name__ == "__main__":
    loop = KarpathyLoop("src/agent/live_agent.py", "tests/immutable_ruler.py")
    
    max_cycles = 3
    print(f"--- Launching Continuous Self-Improvement Cycle (Target: {max_cycles} generations) ---")
    
    for cycle in range(max_cycles):
        print(f"\n==== STARTING EVOLUTION ROUND {cycle + 1}/{max_cycles} ====")
        success = loop.run_iteration(f"Continuous sequence cycle round {cycle + 1}. Optimize telemetry structures.")
        if not success:
            print("[Supervisor Info] Evolution loop terminated safely via Rollback Engine.")
            break
            
    print("\n--- Autonomous Multi-Generation Evolution Suite Concluded ---")
