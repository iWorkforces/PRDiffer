import os


def test_console_logger_uses_stderr_in_stdio(monkeypatch, capsys):
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")

    import ccpragents.infrastructure.logging.console_logger as logger_module

    logger_module._logger_instance = None
    logger = logger_module.ConsoleLogger()

    logger.info("stdio-log-test")
    captured = capsys.readouterr()

    assert "stdio-log-test" in captured.err
    assert captured.out == ""

    # Clean up env for other tests
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
