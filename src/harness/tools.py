import os
import sys
import subprocess
from typing import Dict, Any, List

class AgentToolbox:
    """
    Defines safe sandbox tools that the mutating agent can use 
    to read its workspace, run local sub-tests, or explore context files.
    """
    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def safe_list_dir(self, target_path: str = ".") -> List[str]:
        """Programmatic directory traversal tool for mapping repository modules."""
        full_path = os.path.abspath(os.path.join(self.root_dir, target_path))
        if not full_path.startswith(self.root_dir):
            raise PermissionError("Access Denied: Agent attempted to escape workspace sandbox boundaries.")
        
        if os.path.exists(full_path) and os.path.isdir(full_path):
            return os.listdir(full_path)
        return []

    def safe_read_file(self, target_file: str) -> str:
        """Allows the agent to read source script lines or local reference assets."""
        full_path = os.path.abspath(os.path.join(self.root_dir, target_file))
        if not full_path.startswith(self.root_dir):
            raise PermissionError("Access Denied: Security boundary violation.")
            
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def run_sandbox_sub_test(self, test_script: str) -> Dict[str, Any]:
        """Allows the agent to execute its own custom diagnostic runs during design iterations."""
        full_path = os.path.abspath(os.path.join(self.root_dir, test_script))
        if not full_path.startswith(self.root_dir):
            raise PermissionError("Access Denied: Subprocess execution blocked outside sandbox boundary.")
            
        print(f"[Toolbox] Running internal diagnostic test: {test_script}...")
        result = subprocess.run([sys.executable, full_path], capture_output=True, text=True)
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

if __name__ == "__main__":
    # Test suite tool validation check
    tools = AgentToolbox()
    print("[Toolbox Check] Target directory scan:", tools.safe_list_dir("src/loop"))
