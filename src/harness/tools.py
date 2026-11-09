
"""Filesystem tools with strict project-root containment.

Host-side execution of evaluator scripts is intentionally disabled.
Candidate evaluation belongs in the supervisor's Docker-isolated workflow.
"""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AgentToolbox:
    """Expose limited project filesystem access to the evolving agent.

    Paths are resolved, including symlinks, and must remain descendants of
    the configured project root. Git metadata and local environment secrets
    are protected. Arbitrary host-side script execution is disabled.
    """

    def __init__(self, root_dir: str | os.PathLike[str] | None = None) -> None:
        requested_root = Path(root_dir) if root_dir is not None else PROJECT_ROOT
        self.root_dir = requested_root.resolve(strict=True)

        if not self.root_dir.is_dir():
            raise NotADirectoryError(
                f"Workspace root is not a directory: {self.root_dir}"
            )

    def _resolve_project_path(
        self, target_path: str | os.PathLike[str]
    ) -> Path:
        """Resolve a relative or absolute path and enforce containment."""
        raw_path = Path(target_path)

        candidate = (
            raw_path if raw_path.is_absolute()
            else self.root_dir / raw_path
        )

        resolved = candidate.resolve(strict=False)

        try:
            resolved.relative_to(self.root_dir)
        except ValueError as exc:
            raise PermissionError(
                "Access denied: requested path is outside the workspace root."
            ) from exc

        relative_parts = resolved.relative_to(self.root_dir).parts
        protected = {part.casefold() for part in relative_parts}

        if ".git" in protected or any(
            part == ".env" or part.startswith(".env.")
            for part in protected
        ):
            raise PermissionError(
                "Access denied: Git metadata and local environment secrets "
                "are protected."
            )

        return resolved

    def safe_list_dir(self, target_path: str = ".") -> list[str]:
        """List entries in a directory contained by the project root."""
        full_path = self._resolve_project_path(target_path)

        if not full_path.exists():
            return []

        if not full_path.is_dir():
            raise NotADirectoryError(
                f"Not a directory: {target_path}"
            )

        visible = []

        for entry in full_path.iterdir():
            try:
                self._resolve_project_path(entry)
            except PermissionError:
                continue

            visible.append(entry.name)

        return sorted(visible)

    def safe_read_file(self, target_file: str) -> str:
        """Read a UTF-8 text file contained by the project root."""
        full_path = self._resolve_project_path(target_file)

        if not full_path.exists():
            return ""

        if not full_path.is_file():
            raise IsADirectoryError(
                f"Not a regular file: {target_file}"
            )

        return full_path.read_text(encoding="utf-8-sig")

    def run_sandbox_sub_test(
        self,
        test_script: str,
        timeout_seconds: int = 30,
    ) -> dict:
        """Reject host-side execution of scripts.

        A timeout and script allowlist do not provide OS-level isolation.
        Candidate evaluators must run through the supervisor's Docker-backed
        evaluation workflow instead.
        """
        raise PermissionError(
            "Host-side diagnostic execution is disabled. "
            "Use KarpathyLoop.sandbox_evaluate() for Docker-isolated "
            "candidate evaluation."
        )


if __name__ == "__main__":
    tools = AgentToolbox()

    print(
        "[Toolbox Check] Target directory scan:",
        tools.safe_list_dir("src/loop"),
    )
