
import pytest

from harness.tools import AgentToolbox


def test_rejects_traversal_and_protected_paths(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()

    tools = AgentToolbox(root)

    with pytest.raises(PermissionError):
        tools.safe_read_file("../outside.txt")

    with pytest.raises(PermissionError):
        tools.safe_read_file(".env.local")

    with pytest.raises(PermissionError):
        tools.safe_list_dir(".git")


def test_rejects_symlink_escape(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    link = root / "escape.txt"

    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable")

    with pytest.raises(PermissionError):
        AgentToolbox(root).safe_read_file("escape.txt")


@pytest.mark.parametrize(
    "script",
    [
        "tests/immutable_ruler.py",
        "tests/run_challenge.py",
        "other.py",
    ],
)
def test_host_side_script_execution_is_disabled(tmp_path, script):
    root = tmp_path / "workspace"
    root.mkdir()

    tools = AgentToolbox(root)

    with pytest.raises(
        PermissionError,
        match="Host-side diagnostic execution",
    ):
        tools.run_sandbox_sub_test(script)


def test_blocked_script_does_not_execute(tmp_path):
    root = tmp_path / "workspace"
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True)

    marker = root / "executed.txt"
    script = tests_dir / "run_challenge.py"

    script.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    tools = AgentToolbox(root)

    with pytest.raises(PermissionError):
        tools.run_sandbox_sub_test("tests/run_challenge.py")

    assert not marker.exists()
