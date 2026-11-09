from context.engine import ContextEngine


def test_empty_and_short_history_respect_budget():
    engine = ContextEngine(100)
    assert engine.compress_context() == ""
    engine.add_interaction("user", "hello")
    assert engine.count_tokens(engine.compress_context()) <= 100


def test_oversized_errors_and_unicode_are_bounded_and_deterministic():
    engine = ContextEngine(180)
    engine.add_interaction("error", "Traceback: " + "界🙂failure " * 10000)
    engine.add_interaction("error", "failure: latest structure broke")
    engine.add_interaction("user", "recent context")
    first = engine.compress_context()
    assert first == engine.compress_context()
    assert engine.count_tokens(first) <= 180
    assert "latest structure broke" in first


def test_small_budget_smaller_than_heading_overhead():
    engine = ContextEngine(2)
    engine.add_interaction("error", "failure " * 100)
    result = engine.compress_context()
    assert engine.count_tokens(result) <= 2


def test_long_history_backfills_within_exact_cap():
    engine = ContextEngine(64)
    for i in range(40):
        engine.add_interaction("user", f"message {i} detail")
    result = engine.compress_context()
    assert engine.count_tokens(result) <= 64
    assert "message 39" in result


def test_duplicate_diagnostics_are_rendered_once():
    engine = ContextEngine(300)
    engine.add_interaction("error", "failure: duplicate structural fault")
    engine.add_interaction("error", "failure: duplicate structural fault")
    result = engine.compress_context()
    assert result.count("duplicate structural fault") == 1


def test_multiple_recent_failures_and_exact_boundary():
    engine = ContextEngine(1000)
    engine.add_interaction("error", "failure: first structural fault")
    engine.add_interaction("error", "exception: second structural fault")
    result = engine.compress_context()
    assert "first structural fault" in result
    assert "second structural fault" in result
    exact = engine.count_tokens(result)
    engine.token_limit = exact
    assert engine.compress_context() == result
