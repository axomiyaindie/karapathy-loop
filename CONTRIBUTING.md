# Contributing to karapathy-loop

Thank you for your interest in contributing to **karapathy-loop**!


This document explains the project's architecture, development environment, testing strategy, security requirements, and contribution workflow.

Whether you are fixing a bug, improving the evaluation system, strengthening security, or experimenting with AI-driven software improvement, contributions are welcome.

---

## 1. About the project

`karapathy-loop` is an experimental Recursive Self-Improvement (RSI) framework.

It explores how an AI agent can propose modifications to its own Python software scaffolding, evaluate those modifications, and optionally promote successful candidates.

The project uses an iterative software improvement process:

1. Inspect the current agent implementation.
2. Generate a proposed code modification using an AI provider.
3. Evaluate the proposed candidate against protected evaluation rubrics.
4. Archive unsuccessful candidates for analysis.
5. Optionally promote a candidate that passes all required checks.
6. Repeat the process in subsequent generations.

The project modifies software code, not the internal weights of an AI model.

## 2. Project architecture

The repository is organized around several main components.

### `src/loop/main_loop.py`

The mutation supervisor coordinates the improvement lifecycle.

Responsibilities include:

- Managing generation state.
- Communicating with supported AI providers.
- Constructing mutation prompts.
- Extracting proposed Python source.
- Preparing temporary evaluation workspaces.
- Running protected evaluators.
- Archiving unsuccessful candidates.
- Verifying candidate integrity.
- Managing optional Git promotion.

The supervisor must fail closed when required evaluation infrastructure is unavailable.

### `src/context/engine.py`

The context engine manages the information supplied to the AI provider.

Responsibilities include:

- Maintaining interaction history.
- Counting tokens with `tiktoken`.
- Prioritizing diagnostic information.
- Managing context limits.
- Removing duplicate diagnostic entries.
- Keeping prompts within configured token budgets.

Token counts are estimates and may differ from the tokenizer used by an external AI provider.

### `src/harness/tools.py`

The harness provides controlled access to project files and diagnostic operations.

Responsibilities include:

- Restricting filesystem access to approved project locations.
- Rejecting traversal outside the repository.
- Protecting sensitive files.
- Allowlisting diagnostic scripts.
- Limiting diagnostic execution time.

**Important:** Filesystem path validation is an application-level security control. It is not a substitute for OS-level process isolation.

### `src/agent/live_agent.py`

This is the current production agent implementation.

It is the source from which proposed improvements are generated and the target for successful promotion.

Changes to this file must satisfy both protected evaluation rubrics.

### Protected evaluation system

The project uses two protected evaluation scripts:

- `tests/immutable_ruler.py`
- `tests/run_challenge.py`

These scripts define the evaluation contract and must remain unchanged.

New regression tests should be added separately using the `test_*.py` naming convention.

---

## 3. Candidate evaluation lifecycle

Every proposed source modification must be evaluated before promotion.

The supervisor prepares a temporary workspace and places the exact same candidate source in both expected locations:

- `.agent_sandbox/temp_agent.py`
- `src/agent/live_agent.py`

Both unchanged evaluators then run against that candidate inside Docker.

The evaluation system records a SHA-256 hash of the original candidate source.

Promotion must use the exact candidate that passed evaluation. A candidate must never be silently modified between evaluation and promotion.

### Evaluation requirements

Candidate evaluation must:

- Execute both protected rubrics.
- Use the same candidate source for both evaluations.
- Run inside the OS-isolated container path.
- Mount evaluation inputs read-only.
- Disable container networking.
- Apply CPU, memory, and process limits.
- Apply a timeout.
- Avoid passing provider credentials or Git credentials.
- Avoid mounting the host Git directory or Docker socket.
- Clean up evaluation containers after execution.
- Fail closed if Docker is unavailable or evaluation fails.

Do not replace Docker-backed candidate evaluation with an ordinary Python subprocess.

A temporary directory alone does not provide process isolation.

### Docker security

The container is a defense-in-depth boundary, not a guarantee against every possible escape.

The Docker daemon, host operating system, kernel, and container image remain part of the trusted computing base.

Contributors working on the evaluation infrastructure should pay particular attention to:

- Container privileges.
- Bind mounts and filesystem permissions.
- Image provenance and digest pinning.
- Secret exposure.
- Network isolation.
- Resource exhaustion.
- Container cleanup.
- Timeout handling.

Never weaken these protections to make a test pass.

---

## 4. Development environment

### Requirements

Development is currently documented for Windows using PowerShell.

You will need:

- Python 3.12
- Git
- Docker Desktop with Linux containers
- A supported AI provider account for live supervisor experiments

The normal regression test suite should not require provider credentials or live network access.

### Clone the repository

```powershell
git clone https://github.com/axomiyaindie/karapathy-loop.git
cd karapathy-loop
```

### Create a virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Configure local environment variables

Create a local configuration file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` with your local provider configuration.

Never commit `.env`, API keys, tokens, passwords, or other credentials.

Use `.env.example` for placeholder configuration only.

---

## 5. Running tests

Run the regression suite from the repository root:

```powershell
python -m pytest -v
```

Run the protected evaluators directly:

```powershell
python tests/immutable_ruler.py
python tests/run_challenge.py
```

These direct commands test the current production agent on the host. They do not independently verify Docker isolation.

The supervisor's Docker-backed evaluation is responsible for testing proposed candidates inside the restricted container.

### Testing requirements

Regression tests must:

- Be deterministic.
- Avoid live AI provider requests.
- Avoid real GitHub pushes.
- Avoid autonomous improvement loops.
- Avoid modifying production files.
- Avoid modifying protected evaluation scripts.
- Use mocks or temporary directories when testing external dependencies.
- Clean up temporary files and resources.
- Verify failure conditions as well as successful execution.

When changing the supervisor, add regression tests for the relevant failure cases.

Examples include:

- Empty or invalid model responses.
- Provider authentication failures.
- Candidate hash mismatches.
- Evaluation timeouts.
- Docker execution failures.
- Failed candidate archiving.
- Dirty Git working trees.
- Git commit failures.
- Git push failures.
- Secret detection and redaction.

Do not introduce a test that makes an actual provider request or performs a real remote Git operation.

---

## 6. Contribution guidelines

### Before making changes

1. Read the relevant source files.
2. Understand the existing public interfaces.
3. Check the current Git working tree.
4. Identify the component affected by your change.
5. Review related tests before modifying implementation code.

Preserve existing public interfaces unless a change is explicitly justified and documented.

Prefer focused, incremental modifications over unnecessary architectural rewrites.

### Adding regression tests

Place new tests in the `tests/` directory.

Use names beginning with:

```text
test_*.py
```

For example:

```text
tests/
    immutable_ruler.py
    run_challenge.py
    conftest.py
    test_context_engine.py
    test_harness_security.py
    test_supervisor.py
```

The two protected evaluator scripts must not be modified.

If you discover a weakness in a protected evaluator, document the finding and discuss the required change separately rather than silently changing the rubric.

### Code quality

Contributions should prioritize:

- Clear and maintainable Python code.
- Small, focused changes.
- Explicit error handling.
- Deterministic behavior.
- Secure filesystem operations.
- Resource and timeout limits.
- Testable interfaces.
- Useful documentation.
- Backward compatibility.

Avoid introducing unnecessary dependencies.

---

## 7. Git and promotion safeguards

Git promotion is a sensitive part of this project.

The supervisor must never overwrite unrelated developer changes.

Before enabling commits:

1. Verify that the target production file is clean.
2. Verify that its Git index entry is clean.
3. Confirm that the candidate hash matches the evaluated source.
4. Stage only `src/agent/live_agent.py`.
5. Commit only after both protected rubrics pass.

Never use broad commands such as:

```powershell
git reset --hard
git clean -fd
```

These commands can destroy unrelated user work.

Recovery operations must target only the specific file and index entry involved in the failed promotion.

### Push behavior

A failed remote push must leave a successful local commit intact.

Do not automatically undo a successful local commit simply because an upstream push failed.

### Default promotion configuration

The safe defaults are:

```dotenv
RSI_AUTO_COMMIT=false
RSI_AUTO_PUSH=false
```

Automatic commits require explicit opt-in.

Remote pushes additionally require explicit opt-in.

Contributors must not enable automatic promotion as part of ordinary regression testing.

---

## 8. Documentation requirements

Update documentation when a contribution changes:

- Public interfaces.
- Configuration options.
- Environment variables.
- Installation instructions.
- Evaluation behavior.
- Security boundaries.
- Dependencies.
- Development workflows.

Keep the README beginner-friendly.

Use this document for technical architecture, development details, testing procedures, and contribution requirements.

---

## 9. Suggested contribution areas

There are several areas where contributions can improve the project.

### Evaluation and sandbox security

- Stronger container isolation.
- Verified and pinned container images.
- Better timeout and cleanup handling.
- Additional security regression tests.
- Improved failure reporting.

### Context engineering

- Better diagnostic prioritization.
- More efficient context compression.
- Improved token-budget management.
- Duplicate detection and history handling.

### Mutation supervisor

- More reliable provider response handling.
- Better candidate validation.
- Stronger promotion safeguards.
- Improved mutation metadata and archiving.

### Testing and reliability

- More regression coverage.
- Better failure simulation.
- Cross-platform compatibility.
- Improved integration testing.

### Documentation

- Clearer setup instructions.
- Better architecture explanations.
- More examples.
- Troubleshooting guides.

These are suggested areas, not a requirement to implement any particular feature.

---

## 10. Submitting a contribution

A typical contribution workflow is:

### Step 1: Create a branch

```powershell
git checkout -b feature/your-change
```

### Step 2: Make a focused change

Modify only the files required for your contribution.

### Step 3: Add regression tests

Create or update tests without changing the protected rubrics.

### Step 4: Run the test suite

```powershell
python -m pytest -v
```

### Step 5: Check your diff

```powershell
git diff --check
git status
git diff
```

Review the final changes and make sure no secrets, generated runtime files, or unrelated modifications are included.

### Step 6: Submit a pull request

Push your feature branch to your fork and open a pull request against the main repository:

https://github.com/axomiyaindie/karapathy-loop

Describe:

- What you changed.
- Why the change is needed.
- Which files were affected.
- Which tests you added or ran.
- Any compatibility or security implications.

For security-sensitive changes, explain the threat being addressed and how the new implementation prevents it.

---

## 11. Security disclosures

Please do not publish exploitable security vulnerabilities, credentials, API keys, or sensitive information in public issues.

Provide enough information for the maintainers to investigate the problem safely.

Never include real secrets in bug reports, test fixtures, or pull requests.

---

## 12. Project status

`karapathy-loop` is an experimental project under active development.

Its goal is to explore controlled, test-driven approaches to AI-driven software improvement.

Contributions are welcome, but reliability and security take priority over increasing the autonomy of the system.

**Thank you for helping improve karapathy-loop.**

---
