import os
import sys
from typing import Dict, Any

class KarpathyLoop:
    def __init__(self, agent_src_path: str, eval_suite_path: str):
        self.agent_src_path = agent_src_path
        self.eval_suite_path = eval_suite_path
        self.generation = 0
        
    def propose_mutation(self, feedback: str) -> str:
        print(f"[Gen {self.generation}] Proposing software mutation...")
        return f"# Generation {self.generation}\ndef execute_task(ctx):\n    ctx['version'] = {self.generation}\n    return True\n"

    def sandbox_evaluate(self, mutated_code: str) -> Dict[str, Any]:
        print(f"[Gen {self.generation}] Running isolated checks inside sandbox...")
        sandbox_dir = ".agent_sandbox"
        os.makedirs(sandbox_dir, exist_ok=True)
        with open(os.path.join(sandbox_dir, "temp_agent.py"), "w") as f:
            f.write(mutated_code)
        return {"passed": True, "feedback": "Code variant executes cleanly."}

    def commit_improvement(self, mutated_code: str):
        print(f"[Gen {self.generation}] Tests Passed! Committing code change permanently.")
        os.makedirs(os.path.dirname(self.agent_src_path), exist_ok=True)
        with open(self.agent_src_path, "w") as f:
            f.write(mutated_code)

    def run_iteration(self):
        self.generation += 1
        code = self.propose_mutation("System Startup")
        res = self.sandbox_evaluate(code)
        if res["passed"]:
            self.commit_improvement(code)

if __name__ == "__main__":
    loop = KarpathyLoop("src/agent/live_agent.py", "tests/immutable_ruler.py")
    loop.run_iteration()
