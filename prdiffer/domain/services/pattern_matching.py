"""Pattern matching service interface for domain layer."""

from abc import ABC, abstractmethod


class PatternMatchingServiceInterface(ABC):
    """Abstract base class for pattern matching services.

    This interface defines the contract for services that provide
    pattern matching functionality for file filtering and validation.
    """

    @abstractmethod
    def is_valid_file(self, filename: str) -> bool:
        """Check if a file should be processed based on configured patterns.

        Args:
            filename: The filename to check

        Returns:
            bool: True if the file should be processed, False otherwise
        """
        pass

    @abstractmethod
    def filter_files(self, filenames: list[str]) -> list[str]:
        """Filter a list of filenames based on configured patterns.

        Args:
            filenames: List of filenames to filter

        Returns:
            List of filenames that pass the pattern validation
        """
        pass
