"""Mutation supervisor with candidate-specific, container-isolated evaluation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# SHA-256 of UTF-8 source after BOM removal and newline normalization.
# Stable across Windows, Linux, and macOS line-ending conventions.
TRUSTED_EVALUATOR_HASHES = {
    "immutable_ruler.py": (
        "2196196ACBC7F43FD9642C187A5C9ED5B3AF9397EBD0A65F96B60D6F1C1797B5"
    ),
    "run_challenge.py": (
        "89EBE1730AAB81A311F24C2214E3DF3F7452A8F6DFB1FC49A7733880ED05C77D"
    ),
}

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from context.engine import ContextEngine


class KarpathyLoop:
    """Coordinate mutation, dual-stage evaluation, and guarded promotion."""

    def __init__(
        self,
        agent_src_path: str = "src/agent/live_agent.py",
        eval_suite_path: str = "tests/immutable_ruler.py",
        *,
        token_limit: int | None = None,
        push_remote: bool | None = None,
    ) -> None:
        load_dotenv(PROJECT_ROOT / ".env")

        self.project_root = PROJECT_ROOT
        self.agent_src_path = self._project_path(agent_src_path)
        self.eval_suite_path = self._project_path(eval_suite_path)
        self.challenge_path = self._project_path("tests/run_challenge.py")

        self.sandbox_dir = self.project_root / ".agent_sandbox"
        self.sandbox_file = self.sandbox_dir / "temp_agent.py"
        self.mutation_archive_dir = self.project_root / ".agent_mutations"

        self.generation = self._read_generation()

        self.token_limit = (
            token_limit
            if token_limit is not None
            else int(os.environ.get("RSI_TOKEN_LIMIT", "3500"))
        )

        self.request_token_limit = self._positive_int(
            "RSI_REQUEST_TOKEN_LIMIT", 16000
        )
        self.output_token_reserve = 2048

        self.context_engine = ContextEngine(token_limit=self.token_limit)

        self.max_cycles = self._positive_int("RSI_MAX_CYCLES", 3)
        self.evaluation_timeout = self._positive_int(
            "RSI_EVALUATION_TIMEOUT", 120
        )

        self.push_remote = (
            push_remote
            if push_remote is not None
            else os.environ.get("RSI_AUTO_PUSH", "false").lower() == "true"
        )

        self.auto_commit = (
            os.environ.get("RSI_AUTO_COMMIT", "false").lower() == "true"
        )

        self.docker = shutil.which("docker")

        if not self.eval_suite_path.is_file() or not self.challenge_path.is_file():
            raise FileNotFoundError(
                "Both protected evaluation scripts are required."
            )

        if not self.agent_src_path.parent.is_dir():
            raise FileNotFoundError(
                f"Agent source directory not found: {self.agent_src_path.parent}"
            )

    @staticmethod
    def _positive_int(name: str, default: int) -> int:
        try:
            value = int(os.environ.get(name, str(default)))
        except ValueError as exc:
            raise ValueError(f"{name} must be a positive integer") from exc

        if value < 1:
            raise ValueError(f"{name} must be a positive integer")

        return value

    def _project_path(self, path: str | Path) -> Path:
        candidate = Path(path)

        resolved = (
            candidate
            if candidate.is_absolute()
            else self.project_root / candidate
        ).resolve()

        try:
            resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise PermissionError(
                f"Project path escapes repository root: {path}"
            ) from exc

        return resolved

    @staticmethod
    def _read_generation() -> int:
        try:
            generation = int(os.environ.get("AGENT_GEN", "1"))
        except ValueError as exc:
            raise ValueError(
                "AGENT_GEN must be a positive integer"
            ) from exc

        if generation < 1:
            raise ValueError("AGENT_GEN must be a positive integer")

        return generation

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.project_root).as_posix()

    @staticmethod
    def _normalized_source_hash(content: bytes) -> str:
        """Hash UTF-8 source consistently across operating systems."""
        text = content.decode("utf-8-sig")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest().upper()

    def _load_verified_evaluators(self) -> dict[str, bytes]:
        """Verify trusted evaluator source and return the exact verified bytes."""

        expected_paths = {
            "immutable_ruler.py": (
                self.project_root / "tests" / "immutable_ruler.py"
            ),
            "run_challenge.py": (
                self.project_root / "tests" / "run_challenge.py"
            ),
        }

        if (
            self.eval_suite_path
            != expected_paths["immutable_ruler.py"].resolve()
        ):
            raise PermissionError(
                "The configured immutable evaluator path is not trusted."
            )

        if (
            self.challenge_path
            != expected_paths["run_challenge.py"].resolve()
        ):
            raise PermissionError(
                "The configured challenge evaluator path is not trusted."
            )

        verified: dict[str, bytes] = {}

        for name, path in expected_paths.items():
            try:
                content = path.read_bytes()
                actual_hash = self._normalized_source_hash(content)

            except (OSError, UnicodeError) as exc:
                raise RuntimeError(
                    f"Cannot read protected evaluator: {name}"
                ) from exc

            expected_hash = TRUSTED_EVALUATOR_HASHES[name]

            if actual_hash != expected_hash:
                raise PermissionError(
                    f"Protected evaluator integrity check failed: {name}. "
                    "Evaluation has been stopped."
                )

            verified[name] = content

        return verified

    def get_current_agent_code(self) -> str:
        return self.agent_src_path.read_text(encoding="utf-8")

    def query_live_llm(
        self,
        system_prompt: str,
        user_content: str,
    ) -> str:

        provider = os.environ.get(
            "RSI_LLM_PROVIDER", "anthropic"
        ).strip().lower()

        if provider == "anthropic":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")

            model = os.environ.get("ANTHROPIC_MODEL", "").strip()

            if not model:
                raise RuntimeError("ANTHROPIC_MODEL must be configured")

            from anthropic import Anthropic

            response = Anthropic().messages.create(
                model=model,
                max_tokens=self.output_token_reserve,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_content}
                ],
            )

            blocks = [
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ]

            text = "\n".join(blocks)

        elif provider == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not configured")

            model = os.environ.get("OPENAI_MODEL", "").strip()

            if not model:
                raise RuntimeError("OPENAI_MODEL must be configured")

            from openai import OpenAI

            response = OpenAI().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=self.output_token_reserve,
            )

            text = response.choices[0].message.content or ""

        else:
            raise ValueError(
                f"Unsupported RSI_LLM_PROVIDER '{provider}'"
            )

        if not text.strip():
            raise RuntimeError(
                f"{provider} returned an empty response"
            )

        return text

    @staticmethod
    def _extract_python_code(response: str) -> str:
        matches = re.findall(
            r"```(?:python|py)?\s*(.*?)```",
            response,
            re.S | re.I,
        )

        code = matches[0].strip() if matches else response.strip()

        if not code:
            raise ValueError(
                "The mutation response contained no Python code"
            )

        return code + "\n"

    def propose_mutation(self, feedback: str) -> str:
        system = (
            "Return one complete Python module defining execute_task(ctx). "
            "It must return a real bool on every path and set "
            "loop_stability_factor in ctx. "
            "Do not include credentials or modify evaluation/supervisor files."
        )

        user = (
            f"{self.context_engine.compress_context()}\n\n"
            f"Current agent:\n"
            f"```python\n{self.get_current_agent_code()}\n```\n\n"
            f"Feedback:\n{feedback}"
        )

        estimated = self.context_engine.count_tokens(
            system + "\n" + user
        )

        if (
            estimated + self.output_token_reserve
            > self.request_token_limit
        ):
            raise ValueError(
                "Mutation prompt plus reserved completion exceeds "
                "RSI_REQUEST_TOKEN_LIMIT "
                f"({estimated} + {self.output_token_reserve} "
                f"> {self.request_token_limit})"
            )

        # API/auth/rate-limit errors are surfaced.
        # They never become a fake candidate.
        return self._extract_python_code(
            self.query_live_llm(system, user)
        )

    @staticmethod
    def _evaluation_result(
        name: str,
        returncode: int,
        stdout: str,
        stderr: str,
        duration: float,
        timed_out: bool,
    ) -> dict[str, Any]:

        return {
            "name": name,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "duration_seconds": round(duration, 3),
            "timed_out": timed_out,
            "passed": returncode == 0 and not timed_out,
        }

    @staticmethod
    def _prepare_container_workspace_permissions(workspace: Path) -> None:
        """Make a temporary workspace readable by Docker's unprivileged user.

        POSIX temporary directories commonly start with mode 0700. The
        evaluator container runs as UID/GID 65534, so its read-only bind mount
        still needs searchable directories and readable files. Windows chmod
        has limited POSIX semantics; Docker Desktop additionally enforces the
        host user's file-sharing ACLs.
        """

        root = workspace.resolve()
        if not root.is_dir():
            raise FileNotFoundError(
                f"Container evaluation workspace does not exist: {root}"
            )

        entries = list(root.rglob("*"))
        directories = [
            root,
            *(
                path
                for path in entries
                if not path.is_symlink() and path.is_dir()
            ),
        ]
        files = [
            path
            for path in entries
            if not path.is_symlink() and path.is_file()
        ]

        # Set parent directories first so the unprivileged container user can
        # traverse the tree. The bind mount itself remains read-only.
        for directory in sorted(directories, key=lambda item: len(item.parts)):
            os.chmod(directory, 0o755)

        for file_path in files:
            os.chmod(file_path, 0o644)

    def _run_container_evaluator(
        self,
        workspace: Path,
        script: str,
    ) -> dict[str, Any]:

        name = Path(script).name

        if not self.docker:
            return self._evaluation_result(
                name,
                -1,
                "",
                "Docker is required for candidate evaluation.",
                0,
                False,
            )

        image = os.environ.get(
            "RSI_SANDBOX_IMAGE", "python:3.12-slim"
        )

        container_name = f"rsi-eval-{uuid.uuid4().hex}"

        command = [
            self.docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network=none",
            "--read-only",
            "--cpus=0.5",
            "--memory=256m",
            "--pids-limit=64",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=65534:65534",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--mount",
            f"type=bind,src={workspace.resolve()},dst=/workspace,readonly",
            "--workdir",
            "/workspace",
            image,
            "python",
            script,
        ]

        start = time.monotonic()

        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.evaluation_timeout,
                check=False,
                shell=False,
            )

            return self._evaluation_result(
                name,
                result.returncode,
                result.stdout,
                result.stderr,
                time.monotonic() - start,
                False,
            )

        except subprocess.TimeoutExpired as exc:
            try:
                subprocess.run(
                    [
                        self.docker,
                        "rm",
                        "--force",
                        container_name,
                    ],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    shell=False,
                )

            except (OSError, subprocess.SubprocessError):
                pass

            out = (
                exc.stdout.decode("utf-8", "replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )

            err = (
                exc.stderr.decode("utf-8", "replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )

            return self._evaluation_result(
                name,
                -1,
                out,
                err,
                time.monotonic() - start,
                True,
            )

        except OSError as exc:
            return self._evaluation_result(
                name,
                -1,
                "",
                str(exc),
                time.monotonic() - start,
                False,
            )

    def sandbox_evaluate(
        self,
        mutated_code: str,
    ) -> dict[str, Any]:

        """Run both verified rubrics against the same candidate in Docker."""

        digest = hashlib.sha256(
            mutated_code.encode("utf-8")
        ).hexdigest()

        with tempfile.TemporaryDirectory(
            prefix="karpathy-eval-"
        ) as temp:

            root = Path(temp)

            (root / "tests").mkdir()
            (root / ".agent_sandbox").mkdir()
            (root / "src" / "agent").mkdir(parents=True)

            # Verify both evaluators before copying either one.
            # The exact verified bytes are used in the Docker workspace.
            verified_evaluators = self._load_verified_evaluators()

            (
                root / "tests" / "immutable_ruler.py"
            ).write_bytes(
                verified_evaluators["immutable_ruler.py"]
            )

            (
                root / "tests" / "run_challenge.py"
            ).write_bytes(
                verified_evaluators["run_challenge.py"]
            )

            (
                root / ".agent_sandbox" / "temp_agent.py"
            ).write_text(
                mutated_code,
                encoding="utf-8",
            )

            (
                root / "src" / "agent" / "live_agent.py"
            ).write_text(
                mutated_code,
                encoding="utf-8",
            )

            # Make the workspace accessible to UID/GID 65534 before the
            # read-only bind mount is passed to Docker.
            self._prepare_container_workspace_permissions(root)

            ruler = self._run_container_evaluator(
                root,
                "tests/immutable_ruler.py",
            )

            challenge = self._run_container_evaluator(
                root,
                "tests/run_challenge.py",
            )

            return {
                "passed": (
                    ruler["passed"] and challenge["passed"]
                ),
                "candidate_sha256": digest,
                "evaluations": [ruler, challenge],
                "feedback": "\n".join(
                    f"[{result['name']}] "
                    f"exit={result['returncode']} "
                    f"timeout={result['timed_out']} "
                    f"duration={result['duration_seconds']}s\n"
                    f"{result['stdout']}{result['stderr']}"
                    for result in (ruler, challenge)
                ),
            }

    def archive_failed_mutation(
        self,
        mutated_code: str,
        feedback: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:

        self.mutation_archive_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        digest = hashlib.sha256(
            mutated_code.encode("utf-8")
        ).hexdigest()

        stem = f"generation_{self.generation:04d}_{timestamp}"

        suffix = 0

        while True:
            extra = f"_{suffix}" if suffix else ""

            code_path = (
                self.mutation_archive_dir
                / f"{stem}{extra}.py"
            )

            log_path = (
                self.mutation_archive_dir
                / f"{stem}{extra}.log"
            )

            if not code_path.exists() and not log_path.exists():
                break

            suffix += 1

        code_path.write_text(
            self._redact_sensitive(mutated_code),
            encoding="utf-8",
        )

        record = {
            "generation": self.generation,
            "timestamp_utc": timestamp,
            "candidate_sha256": digest,
            "failure_reason": self._redact_sensitive(feedback),
            "promotion_attempted": bool(
                (metadata or {}).get("promotion_attempted", False)
            ),
            "evaluator_results": (
                (metadata or {}).get("evaluations", [])
            ),
        }

        safe_record = json.loads(
            self._redact_sensitive(
                json.dumps(record, ensure_ascii=False)
            )
        )

        log_path.write_text(
            json.dumps(
                safe_record,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

        return code_path

    @staticmethod
    def _secret_patterns() -> tuple[tuple[str, str], ...]:
        """Return patterns for detecting and redacting common credentials."""

        return (
            (
                r"""(?i)\b(?:api[_-]?key|access[_-]?key|secret[_-]?key|"""
                r"""client[_-]?secret|password|passwd|token|auth[_-]?token|"""
                r"""credential|private[_-]?key)\b\s*[:=]\s*"""
                r"""(['"])[^'"\r\n]{8,}\1""",
                "[REDACTED_CREDENTIAL_ASSIGNMENT]",
            ),
            (
                r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*",
                "Bearer [REDACTED_TOKEN]",
            ),
            (r"\bsk-[A-Za-z0-9_-]{20,}\b", "[REDACTED_SECRET_TOKEN]"),
            (r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", "[REDACTED_GITHUB_TOKEN]"),
            (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "[REDACTED_GITHUB_TOKEN]"),
            (r"\bAIza[0-9A-Za-z_-]{30,}\b", "[REDACTED_GOOGLE_API_KEY]"),
            (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "[REDACTED_SLACK_TOKEN]"),
            (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED_AWS_ACCESS_KEY]"),
            (
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
                r".*?"
                r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                "[REDACTED_PRIVATE_KEY]",
            ),
        )

    def _redact_sensitive(self, text: str) -> str:
        """Redact recognizable credentials before archiving data."""

        redacted = text
        for pattern, replacement in self._secret_patterns():
            redacted = re.sub(pattern, replacement, redacted, flags=re.DOTALL)

        secret_markers = ("key", "token", "secret", "password", "credential")
        for name, value in os.environ.items():
            if (
                value
                and len(value) >= 8
                and any(marker in name.casefold() for marker in secret_markers)
            ):
                redacted = redacted.replace(value, "[REDACTED_ENV_VALUE]")

        return redacted

    def _git(
        self,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:

        return subprocess.run(
            ["git", *args],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=120,
            check=check,
            shell=False,
        )

    def _validate_git_state(self) -> str:
        self._git("rev-parse", "--show-toplevel")

        branch = self._git(
            "branch",
            "--show-current",
        ).stdout.strip()

        if not branch:
            raise RuntimeError(
                "Cannot promote from a detached HEAD"
            )

        self._git(
            "check-ref-format",
            "--branch",
            branch,
        )

        remotes = self._git("remote").stdout.splitlines()

        if "origin" not in remotes:
            raise RuntimeError(
                "Git remote 'origin' is not configured"
            )

        if not self._git(
            "remote",
            "get-url",
            "origin",
        ).stdout.strip():
            raise RuntimeError(
                "Git remote 'origin' has no URL"
            )

        staged = self._git(
            "diff",
            "--cached",
            "--name-only",
        ).stdout.splitlines()

        target = self._relative(self.agent_src_path)

        if staged:
            raise RuntimeError(
                "Refusing to commit while the Git index has staged changes"
            )

        status = self._git(
            "status",
            "--porcelain",
            "--",
            target,
        ).stdout.strip()

        if status:
            raise RuntimeError(
                f"Production target has pre-existing Git changes: {target}"
            )

        return branch

    def _reject_secret_like_code(self, code: str) -> None:
        """Reject candidate code containing recognizable credentials."""

        for pattern, _replacement in self._secret_patterns():
            if re.search(pattern, code, flags=re.DOTALL):
                raise PermissionError(
                    "Candidate appears to contain credentials or private "
                    "key material; promotion blocked."
                )

        secret_markers = ("key", "token", "secret", "password", "credential")
        for name, value in os.environ.items():
            if (
                value
                and len(value) >= 8
                and any(marker in name.casefold() for marker in secret_markers)
                and value in code
            ):
                raise PermissionError(
                    "Candidate contains a configured secret value; "
                    "promotion blocked."
                )

    def _atomic_write_agent(self, code: str) -> None:
        temporary = self.agent_src_path.with_suffix(
            self.agent_src_path.suffix + ".rsi-tmp"
        )

        try:
            temporary.write_text(
                code,
                encoding="utf-8",
            )

            shutil.copystat(
                self.agent_src_path,
                temporary,
            )

            os.replace(
                temporary,
                self.agent_src_path,
            )

        finally:
            if temporary.exists():
                temporary.unlink()

    def commit_improvement(
        self,
        mutated_code: str,
        tested_hash: str,
    ) -> bool:

        """Commit only the tested candidate; optional push follows current branch."""

        digest = hashlib.sha256(
            mutated_code.encode("utf-8")
        ).hexdigest()

        if digest != tested_hash:
            raise RuntimeError(
                "Candidate hash differs from the evaluated source"
            )

        self._reject_secret_like_code(mutated_code)

        branch = self._validate_git_state()

        previous = self.get_current_agent_code()

        previous_head = self._git(
            "rev-parse",
            "HEAD",
        ).stdout.strip()

        self._atomic_write_agent(mutated_code)

        staged = False

        try:
            self._git(
                "add",
                "--",
                self._relative(self.agent_src_path),
            )

            staged = True

            self._git(
                "commit",
                "--only",
                "-m",
                f"RSI: generation {self.generation} validated",
                "--",
                self._relative(self.agent_src_path),
            )

        except Exception:
            current_head = self._git(
                "rev-parse",
                "HEAD",
                check=False,
            ).stdout.strip()

            if current_head != previous_head:
                # A hook may fail after Git already recorded the commit.
                raise

            self._atomic_write_agent(previous)

            if staged:
                self._git(
                    "restore",
                    "--staged",
                    "--",
                    self._relative(self.agent_src_path),
                    check=False,
                )

            raise

        if self.push_remote:
            try:
                self._git(
                    "push",
                    "--set-upstream",
                    "origin",
                    branch,
                )

            except Exception as exc:
                print(
                    f"[Git Warning] Local commit retained; push failed: {exc}"
                )
                return False

        return True


    def run_iteration(
        self,
        baseline_feedback: str = "Improve safe telemetry handling.",
    ) -> bool:

        self.context_engine.add_interaction(
            "system",
            f"Starting generation {self.generation}.",
        )

        code: str | None = None
        evaluation: dict[str, Any] = {}

        try:
            code = self.propose_mutation(baseline_feedback)

            self._reject_secret_like_code(code)

            evaluation = self.sandbox_evaluate(code)

            self.context_engine.add_interaction(
                "evaluation",
                evaluation["feedback"],
            )

            if not evaluation["passed"]:
                self.archive_failed_mutation(
                    code,
                    evaluation["feedback"],
                    evaluation,
                )
                return False

            if not self.auto_commit:
                self.context_engine.add_interaction(
                    "warning",
                    "Both rubrics passed; promotion disabled "
                    "(RSI_AUTO_COMMIT=false).",
                )

                print(
                    "Both evaluators passed. "
                    "Promotion is disabled; no Git changes were made."
                )

                self.generation += 1
                os.environ["AGENT_GEN"] = str(self.generation)

                return True

            evaluation["promotion_attempted"] = True

            pushed = self.commit_improvement(
                code,
                evaluation["candidate_sha256"],
            )

            if not pushed:
                self.context_engine.add_interaction(
                    "warning",
                    "Local commit succeeded; push failed.",
                )

            self.generation += 1
            os.environ["AGENT_GEN"] = str(self.generation)

            return True

        except Exception as exc:
            feedback = f"{type(exc).__name__}: {exc}"

            self.context_engine.add_interaction(
                "error",
                feedback,
            )

            if code is not None:
                try:
                    self.archive_failed_mutation(
                        code,
                        feedback,
                        evaluation,
                    )
                except OSError:
                    pass

            # A candidate that passed evaluation consumes a generation,
            # even if its subsequent Git promotion failed.
            if evaluation.get("passed"):
                self.generation += 1
                os.environ["AGENT_GEN"] = str(self.generation)

            return False


if __name__ == "__main__":
    loop = KarpathyLoop()

    print(
        f"Starting karpathy-loop for at most {loop.max_cycles} cycles."
    )

    for cycle in range(loop.max_cycles):
        print(
            f"\nEvolution round {cycle + 1}/{loop.max_cycles}"
        )

        if not loop.run_iteration(
            f"Evolution cycle {cycle + 1}. Improve telemetry safely."
        ):
            print(
                "Loop stopped after a rejected or failed mutation."
            )
            break
