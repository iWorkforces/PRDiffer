"""Diff utility service interface for domain layer."""

from abc import ABC, abstractmethod


class DiffServiceInterface(ABC):
    """Abstract base class for diff services.

    This interface defines the contract for services that provide
    diff generation and manipulation functionality.
    """

    @abstractmethod
    def build_full_file_patch(self, original_file_str: str, new_file_str: str) -> str:
        """Build a full-file unified diff patch.

        Args:
            original_file_str: Original file content
            new_file_str: New file content

        Returns:
            str: Unified diff patch covering the entire file
        """
        pass

    @abstractmethod
    def decode_if_bytes(self, content: str | bytes | bytearray) -> str:
        """Decode bytes content to string with fallback encoding support.

        Args:
            content: Content that may be bytes, bytearray, or string

        Returns:
            str: Decoded string content, empty string if all decodings fail
        """
        pass

    @abstractmethod
    def extend_patch(self, original_file_str: str, patch_str: str, new_file_str: str = '') -> str:
        """Extend a patch to show full file context.

        Args:
            original_file_str: Original file content
            patch_str: Original patch string
            new_file_str: New file content (optional)

        Returns:
            str: Extended patch with full file context
        """
        pass
