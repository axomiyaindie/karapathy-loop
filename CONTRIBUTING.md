# Contributing to karapathy-loop

We welcome contributions to this recursive self-improvement agent sandbox! Because this system permits an AI agent to programmatically evaluate and rewrite its own codebase components, human development must stick to strict system interface contracts.

## Development Guidelines

1. Maintain Interface Contracts: Any evolutionary modification target (such as src/agent/live_agent.py) must cleanly implement the explicit contract layout expected by the test layer.
2. Isolate the Rubric: Never allow the mutating agent loop to modify files located inside the tests/ directory. If the agent modifies its own grading parameters, it will trigger immediate reward hacking collapse.
3. Sandbox Everything: All tool additions built inside src/harness/tools.py must enforce strict path containment checks to block structural loop breakouts on the local host machine.

## Pull Request Process

- Ensure python src/loop/main_loop.py executes all three baseline evolution rounds without raising runtime errors or dropping rollback checks.
- Verify your local environment file tracking maps correctly by calling git status. Do not include .env tokens inside pull requests.
- Commit using short descriptive updates:
  ```bash
  git commit -m "Feature: Integrate custom exception parsing rules to the context layer"
  ```
