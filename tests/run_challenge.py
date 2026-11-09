import sys
import os
import importlib.util

def execute_performance_challenge() -> bool:
    """
    Simulates a live engineering task for the self-evolving agent.
    The agent must mutate its function to record complex state profiles
    and prove it can log specific operational performance flags.
    """
    print("\n--- Challenge Suite: Initiating Performance Run ---")
    target_agent = "src/agent/live_agent.py"
    
    if not os.path.exists(target_agent):
        print("[Challenge Error] No live agent script found to evaluate.")
        return False

    try:
        # Dynamically load the agent's current deployed generation
        spec = importlib.util.spec_from_file_location("live_agent", target_agent)
        live_agent = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(live_agent)
        
        # Setup an empty telemetry context
        test_context = {}
        
        # Execute the agent function
        success = live_agent.execute_task(test_context)
        
        # Challenge Constraints: The agent passes ONLY if it builds complex state profiles
        print(f"[Challenge Telemetry Logged]: {test_context}")
        
        if not success:
            print("[FAIL] Agent function returned a negative execution code.")
            return False
            
        if "loop_stability_factor" not in test_context:
            print("[FAIL] Optimization Criteria Unmet: Missing 'loop_stability_factor' metric.")
            return False
            
        print("[SUCCESS] The live agent successfully solved the performance tracking challenge!")
        return True
        
    except Exception as e:
        print(f"[CRITICAL] Challenge execution dropped due to a structural exception: {e}")
        return False

if __name__ == "__main__":
    passed = execute_performance_challenge()
    sys.exit(0 if passed else 1)
