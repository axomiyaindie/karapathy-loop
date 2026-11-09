# karapathy-loop

An autonomous framework for Recursive Self-Improvement (RSI) in AI agents. This repository isolates the execution engine, environment harness, and context management layer, allowing an agent to safely mutate, evaluate, and commit versions of its own software scaffolding.

## Motivation and Philosophy

The project name karapathy-loop pays direct homage to Andrej Karpathy and his foundational work in machine learning exploration—specifically his recent open-source engineering scripts (like minGPT, nanoGPT) and automated research iterations. 

In traditional AI systems, optimization happens by modifying static matrix weights. karapathy-loop focuses on the next engineering paradigm: evolving the software scaffolding itself. By treating the outer loop framework, execution toolboxes, and context token summary handlers as standard mutable software scripts, the agent can recursively adapt its own operational strategies grounded by an automated validation system.

---

## Core Architecture Layout

The framework enforces a strict three-tier boundary isolation to ensure secure execution and prevent loop degeneration or reward hacking:

*   The Outer Supervisor Loop (src/loop/main_loop.py): Manages continuous evolution rounds, schedules code mutations, catches runtime failures, and handles localized Git version checkpoints.
*   The Context Engine (src/context/engine.py): Utilizes tiktoken token tracking to calculate data boundaries, compressing historical execution logs and errors to fit prompt window boundaries efficiently.
*   The Sandbox Harness (src/harness/tools.py): Houses strict file-system directory access control structures and terminal subprocess executors for running tests safely.
*   The Decoupled Verifiers (tests/): Contains the immutable_ruler.py rubric and the run_challenge.py performance suite. If a mutated script breaks syntax rules or fails state contract logging constraints, execution is dropped.

---

## The Self-Healing Lifecycle

1. Propose Code Optimization -> Write to Sandbox Workspace
2. Sandbox -> Run Immutable Ruler Verification
3. Check Pass/Fail:
   - If FAIL: Trigger Checkout and Recover -> Revert to last stable commit -> Halt/Log Error Context
   - If PASS: Commit and Upstream Git Push

Detailed step sequence:
1. Mutation: The agent reads its live script profile and drafts a structural alteration.
2. Isolation: The code changes are saved into .agent_sandbox/temp_agent.py to preserve core branch security.
3. Screening: A separate Python subprocess launches the test validation suites.
4. Fault Recovery: If validation returns an error, the Rollback Engine triggers a local git checkout HEAD to purge broken artifacts and preserve stability.
5. Synchronization: If all assertions pass, the code is moved to production, staged, committed, and synced to GitHub upstream.

---

## Getting Started

### Prerequisites
Ensure your local system has Git and Python 3.10+ configured.

### Installation and Local Setup
```bash
# Clone the repository
git clone https://github.com
cd karapathy-loop

# Install package dependencies
pip install -r requirements.txt
```

### Activating Live Model Execution
To transition from local fallback simulation paths to genuine frontier model engineering, configure your API coordinates inside the secure .env workspace:
```text
RSI_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
```

### Executing the Loop
```bash
# Evaluate the live production agent configuration state
python tests/run_challenge.py

# Launch the Multi-Generation Recursive Self-Improvement Supervisor
python src/loop/main_loop.py
```
