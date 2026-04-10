"""Tests for domain interface protocol conformance.

Verifies that infrastructure implementations satisfy the domain-level
Protocol interfaces using runtime_checkable isinstance checks.
"""

import pytest


@pytest.mark.unit
class TestInputValidatorProtocol:
    """Verify InputValidator satisfies InputValidatorProtocol."""

    def test_input_validator_satisfies_protocol(self):
        """Infrastructure InputValidator must satisfy domain protocol."""
        from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol
        from prdiffer.infrastructure.security.input_validator import InputValidator

        validator = InputValidator()
        assert isinstance(validator, InputValidatorProtocol)

    def test_protocol_is_runtime_checkable(self):
        """InputValidatorProtocol must be runtime_checkable."""
        from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol

        assert hasattr(InputValidatorProtocol, "__protocol_attrs__") or hasattr(InputValidatorProtocol, "__abstractmethods__")

    def test_non_conforming_object_fails(self):
        """An object without required methods must not satisfy the protocol."""
        from prdiffer.domain.interfaces.input_validation import InputValidatorProtocol

        class NotAValidator:
            pass

        assert not isinstance(NotAValidator(), InputValidatorProtocol)


@pytest.mark.unit
class TestRequestCoalescingProtocol:
    """Verify RequestCoalescingService satisfies RequestCoalescingProtocol."""

    def test_request_coalescing_satisfies_protocol(self):
        """Infrastructure RequestCoalescingService must satisfy domain protocol."""
        from prdiffer.domain.interfaces.request_coalescing import RequestCoalescingProtocol
        from prdiffer.infrastructure.utils.coalescing_service import RequestCoalescingService

        service = RequestCoalescingService()
        assert isinstance(service, RequestCoalescingProtocol)

    def test_protocol_is_runtime_checkable(self):
        """RequestCoalescingProtocol must be runtime_checkable."""
        from prdiffer.domain.interfaces.request_coalescing import RequestCoalescingProtocol

        assert hasattr(RequestCoalescingProtocol, "__protocol_attrs__") or hasattr(RequestCoalescingProtocol, "__abstractmethods__")

    def test_non_conforming_object_fails(self):
        """An object without required methods must not satisfy the protocol."""
        from prdiffer.domain.interfaces.request_coalescing import RequestCoalescingProtocol

        class NotAService:
            pass

        assert not isinstance(NotAService(), RequestCoalescingProtocol)
