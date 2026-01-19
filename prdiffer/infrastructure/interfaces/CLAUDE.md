# CLAUDE.md - Infrastructure Interfaces

This file provides guidance for working with infrastructure interfaces.

**Current Version:** 0.4.6

## Overview

The `infrastructure/interfaces/` directory is reserved for infrastructure-layer interface definitions. Currently, this directory is empty.

## Purpose

Infrastructure interfaces define contracts for external system integrations that are specific to the infrastructure layer. They complement domain service interfaces by providing infrastructure-specific contracts.

## When to Add Interfaces Here

Add infrastructure interfaces when you need to:
1. **Abstract External Libraries**: Wrap third-party library APIs
2. **Define Infrastructure Contracts**: Specify infrastructure service behavior
3. **Enable Testing**: Allow mocking of infrastructure dependencies
4. **Decouple Implementation**: Separate interface from implementation

## Relationship to Domain Interfaces

**Domain Service Interfaces** (`domain/services/`):
- Define business operation contracts
- Used by domain layer
- Implementation-agnostic

**Infrastructure Interfaces** (`infrastructure/interfaces/`):
- Define infrastructure operation contracts
- Used by infrastructure layer
- May expose infrastructure-specific details

## Examples of Infrastructure Interfaces

**Future examples might include:**
- `GitHubAPIClientInterface` - GitHub API client contract
- `HTTPClientInterface` - HTTP client contract
- `FilesystemInterface` - File system operations contract
- `DatabaseInterface` - Database operations contract

## Interface Structure

```python
"""Infrastructure interface for [external system]."""

from abc import ABC, abstractmethod
from typing import ...

class [ExternalSystem]Interface(ABC):
    """Interface for [external system] operations.

    Defines the contract for interacting with [external system].
    """

    @abstractmethod
    async def [method](self, ...) -> ...:
        """Execute [operation].

        Args:
            ...: Method parameters

        Returns:
            ...: Return value description

        Raises:
            ...: Exceptions that may be raised
        """
        pass
```

## Interface vs. Implementation

**Interface** (`infrastructure/interfaces/`):
- Defines contract (what)
- No implementation details
- Used for dependency injection

**Implementation** (`infrastructure/`):
- Provides concrete implementation (how)
- Contains actual logic
- Implements interface

## When NOT to Add Interfaces

Don't add infrastructure interfaces when:
1. **Domain Interface Exists**: Use domain service interface instead
2. **Simple Wrapper**: Direct library usage is sufficient
3. **No Abstraction Needed**: Implementation is straightforward

## Example: GitHub API Client

**Interface** (`infrastructure/interfaces/github_api_client.py`):
```python
class GitHubAPIClientInterface(ABC):
    """Interface for GitHub API client."""

    @abstractmethod
    async def get_pull_request(self, owner: str, repo: str, number: int) -> PR:
        """Get pull request data."""
        pass
```

**Implementation** (`infrastructure/github/api_client.py`):
```python
class PyGithubAPIClient(GitHubAPIClientInterface):
    """PyGithub implementation of GitHub API client."""

    def __init__(self, token: str):
        self._github = Github(token)

    async def get_pull_request(self, owner: str, repo: str, number: int) -> PR:
        """Get pull request using PyGithub."""
        # Implementation using PyGithub library
        ...
```

## Related Documentation

- `../CLAUDE.md` - Infrastructure layer documentation
- `../../domain/services/CLAUDE.md` - Domain service interfaces documentation
- `../github/CLAUDE.md` - GitHub components documentation
