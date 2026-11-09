# karpathy-loop

An autonomous framework for **Recursive Self-Improvement (RSI)** in AI agents. This repository isolates the execution engine, environment harness, and context management layer to let an agent safely mutate, evaluate, and commit versions of its own software scaffolding.

## 🏗️ Architecture

- **The Outer Loop (`src/loop/`):** Manages the tree-search mutation policy and failure retry logic.
- **The Context Engine (`src/context/`):** Dynamically optimizes agent history summaries and skill file playbooks.
- **The Sandbox Harness (`src/harness/`):** Runs mutated variants inside isolated execution blocks against an **Immutable Ruler** evaluation suite.

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com
cd karpathy-loop

# Install core dependencies
pip install -r requirements.txt
```

*Warning: This framework allows an agent to modify its execution code. Always run this framework inside a secure Docker container or sandboxed environment.*
