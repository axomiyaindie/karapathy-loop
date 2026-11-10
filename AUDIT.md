# Repository Audit

| | |
| --- | --- |
| **Project** | karapathy-loop |
| **Repository** | https://github.com/axomiyaindie/karapathy-loop |
| **Audit status** | Follow-up verification completed on Windows |
| **Python** | 3.12.10 |
| **Docker Engine** | 29.9.2 |
| **Platform** | Windows with Docker Desktop and WSL2 Linux containers |

> [!NOTE]
> This is an audit record, not a security guarantee. Results describe what was tested on Windows at the time of verification. macOS and Linux are not yet verified.

## Table of contents

1. [Audit overview](#1-audit-overview)
2. [Repository findings and corrections](#2-repository-findings-and-corrections)
3. [Mutation evaluation and Docker isolation](#3-mutation-evaluation-and-docker-isolation)
4. [Windows verification results](#4-windows-verification-results)
5. [Secret and Git safety verification](#5-secret-and-git-safety-verification)
6. [Cross-platform compatibility status](#6-cross-platform-compatibility-status)
7. [Remaining recommendations](#7-remaining-recommendations)
8. [Final assessment](#8-final-assessment)

---

## At a glance

| Check | Result |
| --- | --- |
| Windows regression suite | **33 passed, 0 failed** |
| Immutable Ruler (recorded verification) | **PASS** |
| Performance Challenge (recorded verification) | **PASS** |
| Docker-backed dual evaluation (recorded verification) | **PASS** |
| `.env` excluded from Git | **VERIFIED** |
| Automatic commit and push | **DISABLED** by default |
| macOS and Linux | **NOT YET VERIFIED** |

---

## 1. Audit overview

This audit reviews the project's mutation supervisor, context engine, filesystem harness, protected evaluation scripts, configuration, documentation and Git promotion workflow.

The objective was to identify reliability and security weaknesses and improve the framework while preserving its existing architecture and public interfaces.

The two protected evaluation files remain **unchanged**:

- `tests/immutable_ruler.py`
- `tests/run_challenge.py`

Existing user modifications to `src/loop/main_loop.py` and `src/harness/tools.py` were retained as the starting point for the improvements.

The `.env` file was not inspected during the audit. Its Git exclusion was subsequently verified.

---

## 2. Repository findings and corrections

| File | Responsibility | Finding before changes | Correction | Compatibility risk |
| --- | --- | --- | --- | --- |
| `src/loop/main_loop.py` | Provider requests, mutation, evaluation and Git | Single-stage evaluation, unsafe fallback behavior, fixed branch handling and unsafe promotion defaults | Dual-stage Docker evaluation, provider error handling, configurable limits, candidate hashing and guarded Git promotion | Low; principal interfaces retained |
| `src/context/engine.py` | Context history and token management | Diagnostics could exceed the token budget; inefficient history backfilling and no deduplication | Deterministic context management, diagnostic prioritization, deduplication and strict token budgeting | Low; public methods retained |
| `src/harness/tools.py` | Filesystem access and diagnostics | Insufficient execution restrictions and environment-file edge cases | Canonical path validation, protected environment files and unconditional disabling of host-side evaluator execution through the harness | Low; existing method signature retained, but host execution fails closed |
| `src/agent/live_agent.py` | Production agent | Existing baseline implements the required callable and telemetry | Not modified during the hardening work | None |
| `tests/immutable_ruler.py` | Protected syntax and interface evaluation | Existing protected evaluator | Unchanged | None |
| `tests/run_challenge.py` | Protected performance and telemetry evaluation | Existing challenge depended on the production source location | Unchanged; the temporary evaluation workspace supplies the same candidate at the expected location | None |
| `requirements.txt` | Python dependencies | Required dependencies already present | No additional dependencies required | None |
| `.gitignore` | Runtime and secret exclusion | Existing ignore rules required correction | Improved patterns for environment files, runtime directories and generated artifacts | None |
| `.env.example` | Public configuration template | Missing several runtime and promotion settings | Added configurable models, limits, evaluation timeout and safe promotion defaults | Low |
| `README.md` | Project introduction and setup | Documentation did not accurately describe the updated evaluation and promotion workflow | Updated project introduction, installation, configuration and execution guidance | Low |
| `CONTRIBUTING.md` | Development and contribution guidance | Outdated testing and Git recovery recommendations | Updated technical architecture, testing, security and Git contribution requirements | Low |

---

## 3. Mutation evaluation and Docker isolation

The supervisor evaluates proposed candidate code in a temporary workspace. The same candidate source is placed in both expected locations:

- `.agent_sandbox/temp_agent.py`
- `src/agent/live_agent.py`

Both protected evaluators run against that candidate. The supervisor calculates a SHA-256 hash of the original candidate source and returns it with the evaluation results.

### Container restrictions

The inspected Docker execution configuration includes:

| Restriction | Setting |
| --- | --- |
| Networking | `--network=none` |
| Root filesystem | `--read-only` |
| CPU limit | `--cpus=0.5` |
| Memory limit | `--memory=256m` |
| Process limit | `--pids-limit=64` |
| Linux capabilities | `--cap-drop=ALL` |
| Privilege escalation | `--security-opt=no-new-privileges` |
| User | `--user=65534:65534` |
| Evaluation workspace | Read-only bind mount |
| Scratch space | Restricted writable temporary filesystem |
| Time limit | Evaluation timeout, with forced container removal after timeout |

The supervisor **fails closed** when Docker is unavailable or evaluation fails. The container does not intentionally receive provider credentials, the host Git directory or the Docker socket.

> [!WARNING]
> **Security limitation:** These restrictions provide defense in depth, not a guarantee against every possible container escape. The Docker daemon, host operating system, kernel and configured container image remain part of the trusted computing base.

### Host-side evaluator execution

The harness disables host-side evaluator execution through `run_sandbox_sub_test()`. This is an application-level restriction. It does not replace Docker isolation or operating-system security controls.

The protected evaluator scripts remain unchanged and can still be invoked manually from the host for optional checks. Such direct execution **does not provide container isolation**.

---

## 4. Windows verification results

The project was tested on the actual Windows development environment.

### Environment

| Component | Version or configuration |
| --- | --- |
| Operating system | Windows |
| Python | 3.12.10 |
| pytest | 9.2.0 |
| Docker Engine | 29.9.2 |
| Docker runtime | Linux containers through WSL2 |
| Docker CPUs | 4 |
| Docker memory | Approximately 3.33 GiB |

### Automated regression tests

```powershell
python -m pytest -v
```

**Result: 33 passed, 0 failed** on Windows with Python 3.12.10.

<details>
<summary><b>Test coverage</b></summary>

<br>

- Context-engine token-budget enforcement.
- Diagnostic prioritization and deduplication.
- Unicode and oversized diagnostic handling.
- Filesystem traversal protection.
- Symlink escape protection.
- Host-side evaluator execution disabled through the harness.
- Provider response extraction.
- Dual evaluation using the same candidate.
- Provider failure handling.
- Credential detection and redaction across multiple known credential formats.
- Configured environment-secret detection and redaction.
- Git promotion safeguards.
- Failed push handling.
- Commit failure recovery.
- Cross-platform workspace permission handling.
- Git commit path isolation.
- Generation-state handling after evaluation and promotion outcomes.

</details>

### Immutable Ruler

The production agent was copied into the expected candidate location, then evaluated:

```powershell
New-Item -ItemType Directory -Force .agent_sandbox | Out-Null
Copy-Item src\agent\live_agent.py .agent_sandbox\temp_agent.py -Force

python tests\immutable_ruler.py
```

**Result: PASS**

- Syntax validation passed.
- Interface and execution contract passed.

### Performance Challenge

```powershell
python tests\run_challenge.py
```

**Result: PASS.** The existing production agent successfully completed the performance challenge.

Reported telemetry:

```text
generation_telemetry: 1
loop_stability_factor: 0.96
```

### Previously recorded Docker-backed candidate evaluation

The supervisor's `sandbox_evaluate()` method was executed directly, using the existing production agent as the candidate. No LLM request, autonomous mutation cycle, Git commit or Git push was performed during that evaluation.

**Overall result: PASS**

| Evaluator | Result | Exit code | Duration |
| --- | --- | ---: | ---: |
| Immutable Ruler | PASS | 0 | 8.937 seconds |
| Performance Challenge | PASS | 0 | 0.407 seconds |

Both evaluators ran successfully inside Docker against the same candidate source. Docker downloaded the configured `python:3.12-slim` image and executed both evaluations during that verification.

Candidate SHA-256:

```text
47eb44a711233a5c2a88f5b21aa699c613fb73ed83f848690cfe72e2fc522566
```

> [!IMPORTANT]
> **Verification qualification:** The recorded Docker evaluation is evidence of a successful Windows Docker run at that point in the project. The latest 33-test run is a separate regression-test result. The unit-test run does not, by itself, establish that Docker integration was re-tested after every subsequent code change.

### Git validation

```powershell
git diff --check
```

**Result: PASS.** No whitespace errors were reported during the recorded validation.

---

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

No commit or push was performed during the recorded verification process.

---

## 6. Cross-platform compatibility status

The project is intended to support Windows, macOS and Linux. The latest reported regression-test run was performed on **Windows only**.

The Docker execution configuration and workspace permission handling have been reviewed for cross-platform use. However, successful Windows tests do not establish complete compatibility with macOS and Linux.

| Platform | Status |
| --- | --- |
| Windows | Regression suite verified (33 passed) |
| macOS | Not yet verified |
| Linux | Not yet verified |

Recommended platform checks:

- [ ] Run the complete pytest suite on Windows, macOS and Linux.
- [ ] Verify Docker Desktop or Docker Engine availability on each platform.
- [ ] Verify read-only bind mounts and unprivileged container access.
- [ ] Verify temporary workspace permissions.
- [ ] Verify timeout handling and container cleanup.
- [ ] Verify Git promotion and path handling on each platform.

Until those checks are completed, cross-platform support should be considered a development objective rather than a verified guarantee.

---

## 7. Remaining recommendations

Although the current tests and the recorded Docker-backed evaluation passed, several improvements remain recommended.

### Docker image pinning

The current configuration uses a mutable image tag:

```dotenv
RSI_SANDBOX_IMAGE=python:3.12-slim
```

For stronger reproducibility and supply-chain assurance:

- Verify the image provenance.
- Review the image contents.
- Pin a verified immutable image digest.
- Keep the configured image reference consistent across environments.

The Docker pull during the recorded verification reported this digest:

```text
sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
```

> [!CAUTION]
> This digest should be independently verified before it is adopted as the production image reference.

### Additional security testing

- [ ] Test container cleanup after interrupted evaluations.
- [ ] Test hostile candidate filesystem operations.
- [ ] Test resource exhaustion and timeout behavior.
- [ ] Verify that no unintended host paths are mounted.
- [ ] Review Git hooks and remote authentication behavior.
- [ ] Strengthen secret detection and redaction.
- [ ] Test candidate integrity between evaluation and promotion.

### Promotion safeguards

Automatic promotion should remain **disabled** until additional security review is completed.

Successful evaluation of the existing production agent does not establish that arbitrary AI-generated mutations are safe.

---

## 8. Final assessment

| Area | Status |
| --- | --- |
| Context engine regression tests | PASS |
| Harness security regression tests | PASS |
| Supervisor regression tests | PASS |
| Latest Windows regression suite | 33 PASSED |
| Immutable Ruler | PASS in recorded verification |
| Performance Challenge | PASS in recorded verification |
| Docker-backed dual evaluation | PASS in recorded verification |
| Candidate hash reporting | PASS in recorded verification |
| `.env` Git exclusion | VERIFIED |
| Git whitespace validation | PASS in recorded verification |
| Docker image digest pinning | RECOMMENDED |
| Windows regression testing | PASS |
| macOS regression testing | NOT YET VERIFIED |
| Linux regression testing | NOT YET VERIFIED |
| Automatic commit | DISABLED |
| Automatic push | DISABLED |

**Overall assessment: Initial hardening and Windows regression verification successful.**

The framework has passed its latest reported automated regression tests on Windows and has a previously recorded successful Docker-backed evaluation using the existing production agent.

Further security review, native macOS and Linux testing, and evaluation with genuinely new candidate mutations are recommended before enabling autonomous promotion.

---

*Audit record for karapathy-loop, an experimental framework for controlled AI-driven software improvement.*
*Project repository: https://github.com/axomiyaindie/karapathy-loop*