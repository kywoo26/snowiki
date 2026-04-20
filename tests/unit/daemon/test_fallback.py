from __future__ import annotations


def test_execute_with_fallback_uses_fallback_when_daemon_is_unavailable() -> None:
    from snowiki.daemon.fallback import DaemonUnavailableError, execute_with_fallback

    def daemon_call() -> object:
        raise DaemonUnavailableError("connection refused")

    result = execute_with_fallback(
        daemon_call,
        lambda: {"answer": "local-cli-result"},
    )

    assert result == {
        "mode": "fallback",
        "result": {"answer": "local-cli-result"},
    }


def test_execute_with_fallback_prefers_daemon_result_when_available() -> None:
    from snowiki.daemon.fallback import execute_with_fallback

    result = execute_with_fallback(
        lambda: {"answer": "daemon-result"},
        lambda: {"answer": "local-cli-result"},
    )

    assert result == {
        "mode": "daemon",
        "result": {"answer": "daemon-result"},
    }
