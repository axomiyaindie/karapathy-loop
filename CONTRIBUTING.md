# Contributing to karapathy-loop

We welcome contributions to this recursive self-improvement agent sandbox. Because this system permits an AI agent to programmatically evaluate and rewrite its own codebase components, human development must stick to strict system interface contracts.

## Comprehensive Architecture Breakdown

This project functions as a fault-tolerant optimization machine for execution workflows. Contributions must preserve the integrity of the three isolated framework zones.

### 1. The Outer Evolutionary Loop (src/loop/main_loop.py)
The loop engine orchestrates the life cycle of every agent generation. It handles read/write routing from stable files to temporary runtime paths.
- System State Initialization: On launch, the engine checks for the `AGENT_GEN` shell environment variable. If missing, it defaults to generation value 1. This prevents the state memory from resetting between execution round iterations.
- Code Injection Isolation: The loop isolates code changes. The generated python strings are never written directly to active execution blocks. The strings are safely dumped into the `.agent_sandbox/temp_agent.py` folder path first.
- Synchronized Upstream Commits: If a mutation passes validation, the engine makes a decoupled `subprocess.run` system execution check to stage the files with `git add` and commit them locally. It then automatically calls `git push origin main` to sync the state globally.

### 2. The Context Engine (src/context/engine.py)
The context engine manages history data and token limits, acting as the memory core for prompt generation.
- Dynamic Token Management: It wraps the `tiktoken` byte-pair encoder matching frontier deployment architectures. It monitors the precise array size parameters of system text interactions.
- Telemetry Log Compaction: Rather than truncating data chronologically, the loop separates history processing. It prioritizes error traces first. It loops over historical exceptions, parsing strings for keywords like "fail", "syntax", or "error". These critical logs are pinned to the context memory array, while standard interaction history is cleanly backfilled until hitting the 3500-token barrier limit.

### 3. The Sandbox Harness (src/harness/tools.py)
The toolbox provides programmatic tools for environment interaction.
- Strict Directory Containment: The script checks absolute directory paths. Any tool operation (such as `safe_list_dir` or `safe_read_file`) enforces strict boundary validations. It compares target paths using `os.path.abspath`. If an agent tries to traverse paths outside the drive root target (`..`), the system fires a `PermissionError` block to prevent terminal breakout scripts.

### 4. Decoupled Verifiers (tests/)
The validation directory acts as the immutable gatekeeper.
- Syntax Rubrics (`tests/immutable_ruler.py`): This module compiles source code strings using the native `compile(source, path, 'exec')` method. It filters out parse breaks or formatting indent anomalies before anything hits the runtime engine.
- Interface Contracts: The system checks interface criteria via `importlib.util` inspection. It validates that the generated module contains the explicit `execute_task(ctx)` method signature and verifies that its output type evaluates purely to a boolean.
- Performance Challenge Suite (`tests/run_challenge.py`): This validator verifies functional performance. It injects a live tracking dictionary payload, executes the mutated module code, and asserts that the `ctx` array logs complex telemetry states (like the `loop_stability_factor`).

## Degenerative Rollback and Self-Healing Routine

If the validation rubric returns a failure status at any layer, the framework triggers an automated rollback to protect core stability:
1. Rejection: The system logs the failure exception directly into the `ContextEngine` memory to track degeneration history.
2. File-System Recovery: The loop launches a decoupled subprocess command: `git checkout HEAD -- src/agent/live_agent.py`. This clears out modified scripts from the drive and restores files to the last known stable commit.
3. Sandbox Purge: The temporary folder paths are flushed cleanly using `os.remove` utilities before halting the lifecycle loop.

## Pull Request Process

- Ensure python src/loop/main_loop.py executes all baseline evolution rounds without raising runtime errors or dropping rollback checks.
- Verify your local environment file tracking maps correctly by calling git status. Do not include .env tokens inside pull requests.
- Commit using short descriptive updates:
  ```bash
  git commit -m "Feature: Integrate custom exception parsing rules to the context layer"
  ```
