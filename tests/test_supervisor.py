
from pathlib import Path
import hashlib
import os
import subprocess

from loop.main_loop import KarpathyLoop


def make_loop(tmp_path):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.project_root = tmp_path
    loop.eval_suite_path = tmp_path / "tests" / "immutable_ruler.py"
    loop.challenge_path = tmp_path / "tests" / "run_challenge.py"
    loop.generation = 1
    loop.evaluation_timeout = 5
    loop.docker = "docker"

    (tmp_path / "tests").mkdir()
    loop.eval_suite_path.write_text("ruler", encoding="utf-8")
    loop.challenge_path.write_text("challenge", encoding="utf-8")

    return loop


def test_extract_python_and_empty_response():
    assert KarpathyLoop._extract_python_code(
        "```python\nx=1\n```"
    ) == "x=1\n"

    try:
        KarpathyLoop._extract_python_code("  ")
    except ValueError:
        pass
    else:
        raise AssertionError("Empty response should be rejected")


def test_dual_evaluation_uses_same_candidate_in_both_locations(
    tmp_path, monkeypatch
):
    loop = make_loop(tmp_path)

    # Trust only the exact temporary evaluator fixtures used by this test.
    # Production evaluator fingerprints remain unchanged.
    monkeypatch.setattr(
        "loop.main_loop.TRUSTED_EVALUATOR_HASHES",
        {
            "immutable_ruler.py": loop._normalized_source_hash(
                (loop.project_root / "tests" / "immutable_ruler.py").read_bytes()
            ),
            "run_challenge.py": loop._normalized_source_hash(
                (loop.project_root / "tests" / "run_challenge.py").read_bytes()
            ),
        },
    )

    seen = []

    def inspect(workspace, script):
        if "immutable" in script:
            candidate = workspace / ".agent_sandbox" / "temp_agent.py"
        else:
            candidate = workspace / "src" / "agent" / "live_agent.py"

        seen.append(candidate.read_text(encoding="utf-8"))

        return {
            "name": Path(script).name,
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "duration_seconds": 0.01,
            "timed_out": False,
            "passed": True,
        }

    loop._run_container_evaluator = inspect

    candidate_code = "def execute_task(ctx):\n    return True\n"

    result = loop.sandbox_evaluate(candidate_code)

    assert result["passed"] is True
    assert seen == [candidate_code, candidate_code]


def test_api_failure_is_not_converted_to_fallback(monkeypatch):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.request_token_limit = 16000
    loop.output_token_reserve = 2048

    loop.context_engine = type(
        "Context",
        (),
        {
            "compress_context": lambda self: "",
            "count_tokens": lambda self, text: len(text),
        },
    )()

    loop.get_current_agent_code = lambda: "source"
    loop.query_live_llm = lambda *_: (
        _ for _ in ()
    ).throw(RuntimeError("auth failed"))

    try:
        loop.propose_mutation("feedback")
    except RuntimeError as exc:
        assert "auth failed" in str(exc)
    else:
        raise AssertionError("Provider error must propagate")


def test_failed_candidate_archive_redacts_credentials(tmp_path):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.mutation_archive_dir = tmp_path / ".agent_mutations"
    loop.generation = 7

    candidate = (
        "# sk-abcdefghijklmnopqrstuvwxyz0123456789"
        "\\ndef execute_task(ctx): return False\\n"
    )

    path = loop.archive_failed_mutation(candidate, "failure")

    assert (
        "sk-abcdefghijklmnopqrstuvwxyz0123456789"
        not in path.read_text(encoding="utf-8")
    )
    assert list(path.parent.glob("*.log"))


def test_dirty_production_target_blocks_git_promotion(tmp_path):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.project_root = tmp_path
    loop.agent_src_path = tmp_path / "src" / "agent" / "live_agent.py"

    def git(*args, check=True):
        output = (
            " M src/agent/live_agent.py\n"
            if args[:2] == ("status", "--porcelain")
            else ""
        )

        if args[:2] == ("branch", "--show-current"):
            output = "feature\n"

        if args[:1] == ("remote",):
            output = "origin\n"

        return subprocess.CompletedProcess(args, 0, output, "")

    loop._git = git

    try:
        loop._validate_git_state()
    except RuntimeError as exc:
        assert "pre-existing Git changes" in str(exc)
    else:
        raise AssertionError("Dirty production target must block promotion")


def test_failed_push_preserves_successful_local_commit(tmp_path):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.project_root = tmp_path
    loop.agent_src_path = tmp_path / "src" / "agent" / "live_agent.py"
    loop.generation = 4
    loop.push_remote = True
    loop._validate_git_state = lambda: "feature"
    loop.get_current_agent_code = lambda: "old source"

    loop._atomic_write_agent = lambda code: None
    calls = []

    def git(*args, check=True):
        calls.append(args)

        if args[:2] == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, "commit-id\n", "")

        if args[:1] == ("push",):
            raise RuntimeError("remote unavailable")

        return subprocess.CompletedProcess(args, 0, "", "")

    loop._git = git

    tested_hash = hashlib.sha256(b"new source").hexdigest()

    assert loop.commit_improvement("new source", tested_hash) is False
    assert any(call[:1] == ("commit",) for call in calls)
    assert any(call[:1] == ("push",) for call in calls)


def test_commit_failure_restores_only_target_and_its_index_entry(tmp_path):
    loop = KarpathyLoop.__new__(KarpathyLoop)
    loop.project_root = tmp_path
    loop.agent_src_path = tmp_path / "src" / "agent" / "live_agent.py"
    loop.generation = 2
    loop.push_remote = False
    loop._validate_git_state = lambda: "feature"
    loop.get_current_agent_code = lambda: "original"

    writes = []
    loop._atomic_write_agent = writes.append
    calls = []

    def git(*args, check=True):
        calls.append(args)

        if args[:2] == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, "same-head\n", "")

        if args[:1] == ("commit",):
            raise RuntimeError("commit hook rejected")

        return subprocess.CompletedProcess(args, 0, "", "")

    loop._git = git

    candidate = "new content"

    try:
        loop.commit_improvement(
            candidate,
            hashlib.sha256(candidate.encode()).hexdigest(),
        )
    except RuntimeError as exc:
        assert "commit hook rejected" in str(exc)
    else:
        raise AssertionError("Commit failure should be reported")

    assert writes == [candidate, "original"]
    assert any(call[:2] == ("restore", "--staged") for call in calls)


def make_iteration_loop(monkeypatch, auto_commit, evaluation):
    loop = KarpathyLoop.__new__(KarpathyLoop)

    loop.generation = 3
    loop.auto_commit = auto_commit

    loop.context_engine = type(
        "Context",
        (),
        {"add_interaction": lambda self, *args: None},
    )()

    loop.propose_mutation = lambda feedback: "candidate source"
    loop._reject_secret_like_code = lambda code: None
    loop.sandbox_evaluate = lambda code: evaluation
    loop.archive_failed_mutation = lambda *args: None

    monkeypatch.setenv("AGENT_GEN", "3")

    return loop


def test_successful_evaluation_without_commit_increments_generation(monkeypatch):
    evaluation = {
        "passed": True,
        "feedback": "Both evaluators passed.",
        "candidate_sha256": "test-hash",
    }

    loop = make_iteration_loop(monkeypatch, False, evaluation)

    assert loop.run_iteration() is True
    assert loop.generation == 4
    assert os.environ["AGENT_GEN"] == "4"


def test_failed_evaluation_does_not_increment_generation(monkeypatch):
    evaluation = {
        "passed": False,
        "feedback": "Evaluation failed.",
    }

    loop = make_iteration_loop(monkeypatch, False, evaluation)

    assert loop.run_iteration() is False
    assert loop.generation == 3
    assert os.environ["AGENT_GEN"] == "3"


def test_promotion_exception_after_passed_evaluation_increments_generation(
    monkeypatch,
):
    evaluation = {
        "passed": True,
        "feedback": "Both evaluators passed.",
        "candidate_sha256": "test-hash",
    }

    loop = make_iteration_loop(monkeypatch, True, evaluation)

    archived = []
    loop.archive_failed_mutation = lambda *args: archived.append(args)

    def fail_promotion(*args):
        raise RuntimeError("Simulated promotion failure")

    loop.commit_improvement = fail_promotion

    assert loop.run_iteration() is False
    assert loop.generation == 4
    assert os.environ["AGENT_GEN"] == "4"
    assert len(archived) == 1
