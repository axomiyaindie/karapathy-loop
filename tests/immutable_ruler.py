import sys
import os
import importlib.util

def run_immutable_checks(sandbox_file_path: str) -> bool:
    """
    Decoupled verification rubric. If this returns False, 
    the Karpathy Loop will reject and roll back the code mutation.
    """
    print(f"--- Immutable Ruler: Validating {sandbox_file_path} ---")
    
    # Check 1: File must exist and have content
    if not os.path.exists(sandbox_file_path) or os.path.getsize(sandbox_file_path) == 0:
        print("[FAIL] Mutation is empty or file missing.")
        return False
        
    # Check 2: Pure Syntax Check (catches indentation/parse errors before importing)
    try:
        with open(sandbox_file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, sandbox_file_path, 'exec')
        print("[PASS] Syntax validation clean.")
    except Exception as e:
        print(f"[FAIL] Syntax Error detected: {e}")
        return False

    # Check 3: Runtime & Interface Contract Validation
    try:
        # Dynamically load the mutated sandbox module
        spec = importlib.util.spec_from_file_location("temp_agent", sandbox_file_path)
        temp_agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(temp_agent)
        
        # Enforce that the agent MUST implement the 'execute_task' interface function
        if not hasattr(temp_agent, 'execute_task'):
            print("[FAIL] Missing required interface function 'execute_task(ctx)'.")
            return False
            
        # Test execution with a sample runtime context
        mock_ctx = {'history_summary': 'Initial state test'}
        result = temp_agent.execute_task(mock_ctx)
        
        # Enforce strict output type contract
        if not isinstance(result, bool):
            print(f"[FAIL] execute_task output type must be boolean. Got {type(result)}.")
            return False
            
        print("[PASS] Interface and execution contract verified.")
        return True
        
    except Exception as e:
        print(f"[FAIL] Runtime exception during verification execution: {e}")
        return False

if __name__ == "__main__":
    # Test path selector
    target_sandbox = ".agent_sandbox/temp_agent.py"
    passed = run_immutable_checks(target_sandbox)
    sys.exit(0 if passed else 1)
