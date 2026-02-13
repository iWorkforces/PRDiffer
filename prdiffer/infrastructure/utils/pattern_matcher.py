"""Pattern matching utility for file filtering and validation."""

import re
from prdiffer.domain.services import PatternMatchingServiceInterface


class PatternMatcher(PatternMatchingServiceInterface):
    """Utility for matching filenames against patterns with wildcard support.

    This class provides efficient pattern matching for file filtering operations,
    supporting various pattern types including exact matches, wildcards, and
    directory patterns.
    """

    def __init__(
        self, ignore_patterns: list[str], valid_extensions: list[str] | None = None
    ):
        """Initialize the pattern matcher with configuration.

        Args:
            ignore_patterns: List of patterns to ignore (wildcards supported)
            valid_extensions: List of valid file extensions (optional)
        """
        self.ignore_patterns = ignore_patterns
        self.valid_extensions = valid_extensions or []
        self._compiled_patterns = self._compile_patterns(ignore_patterns)

    def _compile_patterns(
        self, patterns: list[str]
    ) -> list[tuple[str, str | re.Pattern]]:
        """Pre-compile regex patterns for efficient matching.

        Args:
            patterns: List of pattern strings to compile

        Returns:
            List of tuples containing (pattern_type, pattern) where:
            - pattern_type: 'regex' for compiled regex, 'string' for string patterns
            - pattern: The compiled regex or original string pattern
        """
        compiled: list[tuple[str, str | re.Pattern]] = []
        for pattern in patterns:
            if "*" in pattern and not pattern.startswith("*."):
                # Convert wildcard pattern to regex
                regex_pattern = pattern.replace("*", ".*")
                try:
                    compiled_regex = re.compile(regex_pattern + "$")
                    compiled.append(("regex", compiled_regex))
                except re.error:
                    # Fall back to original pattern if regex compilation fails
                    compiled.append(("string", pattern))
            else:
                # Simple string patterns (exact matches, *.ext patterns)
                compiled.append(("string", pattern))
        return compiled

    def is_valid_file(self, filename: str) -> bool:
        """Check if a file should be processed based on configured patterns.

        Args:
            filename: The filename to check

        Returns:
            bool: True if the file should be processed, False otherwise
        """
        # Check ignore patterns first
        if self._matches_any_ignore_pattern(filename):
            return False

        # Check valid extensions if specified
        if self.valid_extensions:
            has_valid_extension = any(
                filename.endswith(ext) for ext in self.valid_extensions
            )
            if not has_valid_extension:
                return False

        return True

    def _matches_any_ignore_pattern(self, filename: str) -> bool:
        """Check if filename matches any ignore pattern.

        Args:
            filename: The filename to check

        Returns:
            bool: True if filename matches any ignore pattern, False otherwise
        """
        for pattern_type, pattern in self._compiled_patterns:
            if pattern_type == "regex":
                # Use pre-compiled regex pattern
                if isinstance(pattern, re.Pattern) and pattern.match(filename):
                    return True
            else:
                # Handle string patterns (exact matches, directory patterns, *.ext)
                if isinstance(pattern, str) and self._matches_string_pattern(
                    filename, pattern
                ):
                    return True
        return False

    def _matches_string_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a string pattern.

        Args:
            filename: The filename to check
            pattern: The string pattern to match against

        Returns:
            bool: True if filename matches pattern, False otherwise
        """
        if pattern.endswith("/"):
            # Directory pattern
            return filename.startswith(pattern[:-1])
        else:
            # File pattern - handle wildcards and exact matches
            return self._matches_pattern(filename, pattern)

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a pattern, supporting wildcards.

        Args:
            filename: The filename to check
            pattern: The pattern to match against (supports * wildcard)

        Returns:
            bool: True if filename matches pattern, False otherwise
        """
        # Handle exact matches
        if filename == pattern:
            return True

        # Handle wildcard patterns like *.lock
        if pattern.startswith("*."):
            # Pattern like *.lock - check if filename ends with the extension
            extension = pattern[1:]  # Remove the * (becomes .lock)
            return filename.endswith(extension)

        # Handle other wildcard patterns if needed
        if "*" in pattern:
            # Convert pattern to regex for more complex matching
            regex_pattern = pattern.replace("*", ".*")
            return bool(re.match(regex_pattern + "$", filename))

        # Simple suffix matching (for backward compatibility)
        return filename.endswith(pattern)

    def filter_files(self, filenames: list[str]) -> list[str]:
        """Filter a list of filenames based on configured patterns.

        Args:
            filenames: List of filenames to filter

        Returns:
            List of filenames that pass the pattern validation
        """
        return [filename for filename in filenames if self.is_valid_file(filename)]


def get_pattern_matcher(
    ignore_patterns: list[str], valid_extensions: list[str] | None = None
) -> PatternMatcher:
    """Get a configured pattern matcher instance.

    Args:
        ignore_patterns: List of patterns to ignore
        valid_extensions: List of valid file extensions (optional)

    Returns:
        PatternMatcher: Configured pattern matcher instance
    """
    return PatternMatcher(ignore_patterns, valid_extensions)
