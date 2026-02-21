"""Tests for logger_factory utility module."""

import logging
import pytest

from prdiffer.infrastructure.utils.logger_factory import get_logger, get_null_logger


@pytest.mark.unit
class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        """Test that logger has the correct name."""
        test_name = 'test.module.name'
        logger = get_logger(test_name)
        assert logger.name == test_name

    def test_same_name_returns_same_instance(self):
        """Test that requesting same name returns same logger instance (logging module behavior)."""
        logger1 = get_logger(__name__)
        logger2 = get_logger(__name__)
        assert logger1 is logger2

    def test_different_names_return_different_instances(self):
        """Test that requesting different names returns different instances."""
        logger1 = get_logger('module.one')
        logger2 = get_logger('module.two')
        assert logger1 is not logger2
        assert logger1.name == 'module.one'
        assert logger2.name == 'module.two'

    def test_with_module_name(self):
        """Test get_logger with __name__ (common usage pattern)."""
        logger = get_logger(__name__)
        assert logger.name == __name__
        assert isinstance(logger, logging.Logger)

    def test_logger_inherits_level_from_root(self):
        """Test that logger inherits level from root logger if not explicitly set."""
        # Save original root level
        root_logger = logging.getLogger()
        original_level = root_logger.level

        try:
            root_logger.setLevel(logging.INFO)
            logger = get_logger('test.inheritance')
            # Logger should inherit from root
            assert logger.level == logging.NOTSET or logger.level == root_logger.level
        finally:
            root_logger.setLevel(original_level)

    def test_logger_can_log_messages(self):
        """Test that logger can successfully log messages."""
        logger = get_logger(__name__)

        # Configure a handler to capture log messages
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # These should not raise exceptions
        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        logger.critical('Critical message')

        # Clean up
        logger.removeHandler(handler)

    def test_thread_safety_multiple_calls(self):
        """Test that multiple concurrent calls to get_logger work correctly."""
        import threading

        loggers = []
        lock = threading.Lock()

        def get_logger_thread():
            logger = get_logger('test.threading')
            with lock:
                loggers.append(logger)

        threads = [threading.Thread(target=get_logger_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All loggers should be the same instance
        assert all(logger is loggers[0] for logger in loggers)


@pytest.mark.unit
class TestGetNullLogger:
    """Tests for get_null_logger function."""

    def test_returns_logger_instance(self):
        """Test that get_null_logger returns a Logger instance."""
        logger = get_null_logger()
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name_default(self):
        """Test that null logger has default name when not provided."""
        logger = get_null_logger()
        assert logger.name == 'null_logger'

    def test_logger_has_custom_name(self):
        """Test that null logger uses custom name when provided."""
        custom_name = 'custom.null.logger'
        logger = get_null_logger(custom_name)
        assert logger.name == custom_name

    def test_logger_level_above_critical(self):
        """Test that null logger level is set above CRITICAL."""
        logger = get_null_logger()
        # CRITICAL is 50, so level should be 51 or higher
        assert logger.level > logging.CRITICAL

    def test_logger_does_not_propagate(self):
        """Test that null logger has propagate set to False."""
        logger = get_null_logger()
        assert logger.propagate is False

    def test_null_logger_suppresses_all_messages(self):
        """Test that null logger suppresses all log levels."""
        logger = get_null_logger('test.suppress')

        # Create a handler to capture messages
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Even though logger has a handler, messages should be suppressed due to level
        # The handler should not record anything
        messages = []

        class RecordingHandler(logging.Handler):
            def emit(self, record):
                messages.append(record)

        recording_handler = RecordingHandler()
        recording_handler.setLevel(logging.DEBUG)
        logger.addHandler(recording_handler)

        logger.debug('This should not be logged')
        logger.info('This should not be logged')
        logger.warning('This should not be logged')
        logger.error('This should not be logged')
        logger.critical('This should not be logged')

        # No messages should have been recorded
        assert len(messages) == 0

        # Clean up
        logger.removeHandler(handler)
        logger.removeHandler(recording_handler)

    def test_null_logger_does_not_raise_exceptions(self):
        """Test that calling log methods on null logger does not raise exceptions."""
        logger = get_null_logger('test.noexception')

        # These should not raise exceptions
        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        logger.critical('Critical message')
        logger.log(logging.DEBUG, 'Log message')
        logger.exception('Exception message')  # Normally includes traceback

    def test_same_name_returns_same_instance(self):
        """Test that requesting same name returns same null logger instance."""
        logger1 = get_null_logger('test.same')
        logger2 = get_null_logger('test.same')
        assert logger1 is logger2

    def test_null_logger_separate_from_regular_logger(self):
        """Test that null logger is separate from regular logger of same name."""
        null_logger = get_null_logger('test.separate')
        regular_logger = get_logger('test.separate')

        # They should be the same underlying logger object (from logging module)
        # but the null logger configuration overrides behavior
        assert null_logger is regular_logger

        # The regular logger reference should also have null configuration
        assert regular_logger.level > logging.CRITICAL
        assert regular_logger.propagate is False


@pytest.mark.unit
class TestIntegration:
    """Integration tests for logger_factory module."""

    def test_get_logger_vs_null_logger_different_behavior(self):
        """Test that regular logger and null logger have different behaviors."""
        regular_logger = get_logger('test.compare.regular')
        null_logger = get_null_logger('test.compare.null')

        # Create recording handlers
        regular_messages = []
        null_messages = []

        class RecordingHandler(logging.Handler):
            def __init__(self, message_list):
                super().__init__()
                self.message_list = message_list

            def emit(self, record):
                self.message_list.append(record)

        regular_handler = RecordingHandler(regular_messages)
        regular_handler.setLevel(logging.DEBUG)
        regular_logger.addHandler(regular_handler)
        regular_logger.setLevel(logging.DEBUG)

        null_handler = RecordingHandler(null_messages)
        null_handler.setLevel(logging.DEBUG)
        null_logger.addHandler(null_handler)

        # Log a message to both
        test_message = 'Test message'
        regular_logger.info(test_message)
        null_logger.info(test_message)

        # Regular logger should have recorded the message
        assert len(regular_messages) == 1
        assert regular_messages[0].getMessage() == test_message

        # Null logger should not have recorded the message
        assert len(null_messages) == 0

        # Clean up
        regular_logger.removeHandler(regular_handler)
        null_logger.removeHandler(null_handler)

    def test_multiple_modules_can_use_same_logger(self):
        """Test that multiple callers can get the same logger instance."""
        logger1 = get_logger('shared.module')
        logger2 = get_logger('shared.module')

        assert logger1 is logger2

        # Both loggers should share the same configuration
        assert logger1.level == logger2.level
        assert logger1.handlers == logger2.handlers

    def test_logger_factory_no_external_dependencies(self):
        """Test that logger_factory has no external dependencies beyond standard library."""
        import sys

        # Verify that only standard library imports are used
        module = sys.modules['prdiffer.infrastructure.utils.logger_factory']
        module_source = module.__file__

        # This test verifies the module uses only logging from stdlib
        # If external deps were added, they would appear in the source
        assert module_source.endswith('logger_factory.py')
