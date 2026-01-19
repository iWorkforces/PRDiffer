# CLAUDE.md - Application Services

This file provides guidance for working with application services.

**Current Version:** 0.4.7

## Overview

The `application/services/` directory is reserved for application-layer services. Currently, this directory is empty.

## Purpose

Application services orchestrate business logic and coordinate interactions between:
- Domain use cases
- Infrastructure implementations
- Application components

## When to Add Services Here

Add application services when you need to:
1. **Orchestrate Multiple Use Cases**: Coordinate multiple domain use cases
2. **Implement Application Logic**: Add logic specific to the application layer
3. **Coordinate External Services**: Manage interactions with external systems
4. **Implement Workflows**: Create multi-step workflows

## Examples of Application Services

**Future examples might include:**
- `PRReviewService` - Orchestrates PR review workflow
- `AnalysisService` - Coordinates diff analysis
- `NotificationService` - Manages notifications
- `ReportService` - Generates reports

## Service Structure

```python
"""Application service for [feature]."""

from prdiffer.domain.usecases import [UseCase]
from prdiffer.infrastructure import [Repository]

class [Service]:
    """Application service for [feature].

    Coordinates domain use cases with infrastructure implementations.
    """

    def __init__(
        self,
        use_case: [UseCase],
        repository: [Repository],
        # ... other dependencies
    ):
        """Initialize service with dependencies."""
        self._use_case = use_case
        self._repository = repository

    async def [method](self, ...) -> ...:
        """Execute [operation].

        Coordinates the workflow for [feature].
        """
        # Implementation
```

## Difference from Domain Use Cases

| Aspect | Domain Use Cases | Application Services |
|--------|------------------|---------------------|
| Location | `domain/usecases/` | `application/services/` |
| Purpose | Single business operation | Multi-step workflow |
| Dependencies | Repository interfaces | Concrete implementations |
| Logic | Pure business logic | Application orchestration |

## When NOT to Add Services

Don't add application services when:
1. **Single Operation**: A domain use case is sufficient
2. **Infrastructure**: Logic belongs in infrastructure layer
3. **Domain Logic**: Logic belongs in domain layer

## Related Documentation

- `../CLAUDE.md` - Application layer documentation
- `../components/CLAUDE.md` - Application components documentation
- `../../domain/usecases/CLAUDE.md` - Domain use cases documentation
