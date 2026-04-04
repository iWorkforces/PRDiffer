"""Pattern matching utility for file filtering and validation."""

import re
from prdiffer.domain.services import PatternMatchingServiceInterface


class PatternMatcher(PatternMatchingServiceInterface):
    """Pattern matcher for file filtering with wildcard support."""

    def __init__(self, ignore_patterns: list[str], valid_extensions: list[str] | None = None):
        self.ignore_patterns = ignore_patterns
        self.valid_extensions = valid_extensions or []
        self._compiled_patterns = self._compile_patterns(ignore_patterns)

    def _compile_patterns(self, patterns: list[str]) -> list[tuple[str, str | re.Pattern[str]]]:
        compiled: list[tuple[str, str | re.Pattern[str]]] = []
        for pattern in patterns:
            if "*" in pattern and not pattern.startswith("*."):
                regex_pattern = pattern.replace("*", ".*")
                try:
                    compiled_regex = re.compile(regex_pattern + "$")
                    compiled.append(("regex", compiled_regex))
                except re.error:
                    compiled.append(("string", pattern))
            else:
                compiled.append(("string", pattern))
        return compiled

    def is_valid_file(self, filename: str) -> bool:
        """Check if a file should be processed based on configured patterns."""
        if self._matches_any_ignore_pattern(filename):
            return False

        if self.valid_extensions:
            has_valid_extension = any(filename.endswith(ext) for ext in self.valid_extensions)
            if not has_valid_extension:
                return False

        return True

    def _matches_any_ignore_pattern(self, filename: str) -> bool:
        """Check if filename matches any ignore pattern."""
        for pattern_type, pattern in self._compiled_patterns:
            if pattern_type == "regex":
                if isinstance(pattern, re.Pattern) and pattern.match(filename):
                    return True
            else:
                if isinstance(pattern, str) and self._matches_string_pattern(filename, pattern):
                    return True
        return False

    def _matches_string_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a string pattern."""
        if pattern.endswith("/"):
            return filename.startswith(pattern[:-1])
        # File pattern - handle wildcards and exact matches
        return self._matches_pattern(filename, pattern)

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a pattern, supporting wildcards."""
        if filename == pattern:
            return True

        if pattern.startswith("*."):
            extension = pattern[1:]
            return filename.endswith(extension)

        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            return bool(re.match(regex_pattern + "$", filename))

        return filename.endswith(pattern)

    def filter_files(self, filenames: list[str]) -> list[str]:
        """Filter a list of filenames based on configured patterns."""
        return [filename for filename in filenames if self.is_valid_file(filename)]


def get_pattern_matcher(ignore_patterns: list[str], valid_extensions: list[str] | None = None) -> PatternMatcher:
    """Get a configured pattern matcher instance."""
    return PatternMatcher(ignore_patterns, valid_extensions)
