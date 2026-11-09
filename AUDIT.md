# Repository Audit

**Project:** karapathy-loop
**Repository:** https://github.com/axomiyaindie/karapathy-loop
**Audit status:** Follow-up verification completed on Windows
**Python:** 3.12.10
**Docker Engine:** 29.9.2
**Platform:** Windows with Docker Desktop and WSL2 Linux containers

---

## 1. Audit overview

This audit reviews the project's mutation supervisor, context engine, filesystem harness, protected evaluation scripts, configuration, documentation, and Git promotion workflow.

The objective was to identify reliability and security weaknesses and improve the framework while preserving its existing architecture and public interfaces.

The two protected evaluation files remain unchanged:

- `tests/immutable_ruler.py`
- `tests/run_challenge.py`

Existing user modifications to `src/loop/main_loop.py` and `src/harness/tools.py` were retained as the starting point for the improvements.

The `.env` file was not inspected during the audit. Its Git exclusion was subsequently verified.

## 2. Repository findings and corrections

| File | Responsibility | Finding before changes | Correction | Compatibility risk |
|---|---|---|---|---|
| `src/loop/main_loop.py` | Provider requests, mutation, evaluation and Git | Single-stage evaluation, unsafe fallback behavior, fixed branch handling and unsafe promotion defaults | Dual-stage Docker evaluation, provider error handling, configurable limits, candidate hashing and guarded Git promotion | Low; principal interfaces retained |
| `src/context/engine.py` | Context history and token management | Diagnostics could exceed the token budget; inefficient history backfilling and no deduplication | Deterministic context management, diagnostic prioritization, deduplication and strict token budgeting | Low; public methods retained |
| `src/harness/tools.py` | Filesystem access and diagnostics | Insufficient execution restrictions and environment-file edge cases | Canonical path validation, protected environment files and diagnostic execution allowlist | Low; execution allowlist narrows permitted operations |
| `src/agent/live_agent.py` | Production agent | Existing baseline implements the required callable and telemetry | Not modified during the hardening work | None |
| `tests/immutable_ruler.py` | Protected syntax and interface evaluation | Existing protected evaluator | Unchanged | None |
| `tests/run_challenge.py` | Protected performance and telemetry evaluation | Existing challenge depended on the production source location | Unchanged; temporary evaluation workspace supplies the same candidate at the expected location | None |
| `requirements.txt` | Python dependencies | Required dependencies already present | No additional dependencies required | None |
| `.gitignore` | Runtime and secret exclusion | Existing ignore rules required correction | Improved patterns for environment files, runtime directories and generated artifacts | None |
| `.env.example` | Public configuration template | Missing several runtime and promotion settings | Added configurable models, limits, evaluation timeout and safe promotion defaults | Low |
| `README.md` | Project introduction and setup | Documentation did not accurately describe the updated evaluation and promotion workflow | Updated project introduction, installation, configuration and execution guidance | Low |
| `CONTRIBUTING.md` | Development and contribution guidance | Outdated testing and Git recovery recommendations | Updated technical architecture, testing, security and Git contribution requirements | Low |

## 3. Mutation evaluation and Docker isolation

The supervisor evaluates proposed candidate code in a temporary workspace.

The same candidate source is placed in both expected locations:

- `.agent_sandbox/temp_agent.py`
- `src/agent/live_agent.py`

Both protected evaluators run against that candidate.

The supervisor calculates a SHA-256 hash of the original candidate source and returns it with the evaluation results.

### Container restrictions

The inspected Docker execution configuration includes:

- `--network=none`
- `--read-only`
- `--cpus=0.5`
- `--memory=256m`
- `--pids-limit=64`
- `--cap-drop=ALL`
- `--security-opt=no-new-privileges`
- `--user=65534:65534`
- Read-only bind mount for the temporary evaluation workspace
- Restricted writable temporary filesystem
- Evaluation timeout
- Forced container removal after timeout

The supervisor fails closed when Docker is unavailable or evaluation fails.

The container does not intentionally receive provider credentials, the host Git directory, or the Docker socket.

**Security limitation:** These restrictions provide defense in depth, not a guarantee against every possible container escape. The Docker daemon, host operating system, kernel and configured container image remain part of the trusted computing base.

## 4. Windows verification results

The project was subsequently tested on the actual Windows development environment.

### Environment

| Component | Version or configuration |
|---|---|
| Operating system | Windows |
| Python | 3.12.10 |
| pytest | 9.2.0 |
| Docker Engine | 29.9.2 |
| Docker runtime | Linux containers through WSL2 |
| Docker CPUs | 4 |
| Docker memory | Approximately 3.33 GiB |

### Automated regression tests

Command:

```powershell
py -m pytest -v
```

**22 tests passed**

All 22 regression tests passed.

Coverage included:

- Context-engine token-budget enforcement.
- Diagnostic prioritization and deduplication.
- Unicode and oversized diagnostic handling.
- Filesystem traversal protection.
- Symlink escape protection.
- Diagnostic execution allowlisting.
- Provider response extraction.
- Dual evaluation using the same candidate.
- Provider failure handling.
- Credential redaction.
- Git promotion safeguards.
- Failed push handling.
- Commit failure recovery.

### Immutable Ruler

The production agent was copied into the expected candidate location.

Command:

```powershell
New-Item -ItemType Directory -Force .agent_sandbox | Out-Null

Copy-Item src\agent\live_agent.py .agent_sandbox\temp_agent.py -Force

py tests/immutable_ruler.py
```

**Result: PASS**

- Syntax validation passed.
- Interface and execution contract passed.

### Performance Challenge

Command:

```powershell
py tests/run_challenge.py
```

**Result: PASS**

Reported telemetry:

```text
generation_telemetry: 1
loop_stability_factor: 0.96
```

The existing production agent successfully completed the performance challenge.

### Actual Docker-backed candidate evaluation

The supervisor's `sandbox_evaluate()` method was executed directly using the existing production agent as the candidate.

No LLM request, autonomous mutation cycle, Git commit or Git push was performed.

**Overall result: PASS**

| Evaluator | Result | Exit code | Duration |
|---|---|---:|---:|
| Immutable Ruler | PASS | 0 | 8.937 seconds |
| Performance Challenge | PASS | 0 | 0.407 seconds |

Both evaluators ran successfully inside Docker against the same candidate source.

Candidate SHA-256:

```text
47eb44a711233a5c2a88f5b21aa699c613fb73ed83f848690cfe72e2fc522566
```

Docker successfully downloaded the configured `python:3.12-slim` image and executed both evaluations.

### Git validation

Command:

```powershell
git diff --check
```

**Result: PASS**

No whitespace errors were reported.

## 5. Secret and Git safety verification

The following commands were executed:

```powershell
git ls-files .env
git check-ignore .env
```

Results:

- `.env` is not tracked by Git.
- `.env` is ignored by Git.
- The `.env` file contents were not inspected.
- Automatic commits remain disabled by default.
- Automatic pushes remain disabled by default.

Current safe configuration:

```dotenv
RSI_AUTO_COMMIT=false
RSI_AUTO_PUSH=false
```

No commit or push was performed during the verification process.

## 6. Remaining recommendations

Although the current tests and Docker-backed evaluation passed, several improvements remain recommended.

### Docker image pinning

The current configuration uses:

```dotenv
RSI_SANDBOX_IMAGE=python:3.12-slim
```

This is a mutable image tag.

For stronger reproducibility and supply-chain assurance:

- Verify the image provenance.
- Review the image contents.
- Pin a verified immutable image digest.
- Keep the configured image reference consistent across environments.

The Docker pull during verification reported:

```text
sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
```

This digest should be independently verified before being adopted as the production image reference.

### Additional security testing

Recommended future work:

- Test container cleanup after interrupted evaluations.
- Test hostile candidate filesystem operations.
- Test resource exhaustion and timeout behavior.
- Verify that no unintended host paths are mounted.
- Review Git hooks and remote authentication behavior.
- Strengthen secret detection and redaction.
- Test candidate integrity between evaluation and promotion.

### Promotion safeguards

Automatic promotion should remain disabled until additional security review is completed.

Successful evaluation of the existing production agent does not establish that arbitrary AI-generated mutations are safe.

## 7. Final assessment

| Area | Status |
|---|---|
| Context engine regression tests | PASS |
| Harness security regression tests | PASS |
| Supervisor regression tests | PASS |
| Immutable Ruler | PASS |
| Performance Challenge | PASS |
| Docker-backed dual evaluation | PASS |
| Candidate hash reporting | PASS |
| `.env` Git exclusion | VERIFIED |
| Git whitespace validation | PASS |
| Docker image digest pinning | RECOMMENDED |
| Automatic commit | DISABLED |
| Automatic push | DISABLED |

**Overall assessment: Initial hardening and local verification successful.**

The framework has passed its current automated tests and an actual Docker-backed evaluation using the existing production agent.

Further security review and testing with genuinely new candidate mutations are recommended before enabling autonomous promotion.

---

*Audit record for karapathy-loop — an experimental framework for controlled AI-driven software improvement.*

*Project repository: https://github.com/axomiyaindie/karapathy-loop*
