# AGENTS.md - Infrastructure VCS Providers

Multi-provider VCS abstraction: GitHub, GitLab, Bitbucket (extensible).

## OVERVIEW
VCS provider implementations with VCSDiffRepositoryInterface. Auto-detection via registry pattern.

## STRUCTURE
```
prdiffer/infrastructure/vcs_providers/
├── github_repository.py    # GitHubVCSRepository (production)
├── gitlab_repository.py    # GitLabVCSRepository (mock/stub)
└── *_repository.py         # Additional providers (extensible)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| **Add provider** | New `*_repository.py` | Implement VCSDiffRepositoryInterface |
| **Register provider** | `domain/vcs_provider_registry.py` | Use `register_provider()` |
| **GitHub impl** | `github_repository.py` | Wraps GitHubPRDiffRepository |
| **GitLab impl** | `gitlab_repository.py` | Stub implementation |

## CONVENTIONS

- **Implement VCSDiffRepositoryInterface** (domain layer contract)
- **Async methods only** (anyio primitives)
- **URL pattern matching** via `supports_repository()` method
- **Register in VCSProviderRegistry** for auto-detection
- **Wrap with retry + circuit breaker** for external API calls

## Common Patterns

### VCS Repository Implementation
```python
from prdiffer.domain.interfaces.vcs_provider import VCSDiffRepositoryInterface
from prdiffer.infrastructure.utils.retry_handler import get_retry_handler
import anyio

class GitHubVCSRepository(VCSDiffRepositoryInterface):
    '''GitHub VCS provider with retry + circuit breaker'''
    
    def __init__(self):
        self._retry_handler = get_retry_handler()
    
    def supports_repository(self, url: str) -> bool:
        '''Auto-detect GitHub URLs'''
        return 'github.com' in url
    
    async def get_pr_diff_async(self, url: str) -> PRDiff:
        '''Async diff retrieval with retry'''
        return await self._retry_handler.retry_async(
            lambda: self._fetch_diff(url)
        )
```

### Provider Registration (Auto-Detection)
```python
from prdiffer.domain.vcs_provider_registry import VCSProviderRegistry

# Register providers in registry
registry = VCSProviderRegistry()
registry.register_provider(GitHubVCSRepository())
registry.register_provider(GitLabVCSRepository())

# Auto-detect provider from URL
provider = registry.get_provider('https://github.com/owner/repo/pull/123')
```

## Anti-Patterns

- ❌ Synchronous blocking code (use async/await with anyio)
- ❌ Direct API calls without retry wrapper
- ❌ Missing circuit breaker integration
- ❌ Hardcoded provider selection (use registry auto-detection)
- ❌ Using asyncio primitives (use anyio instead)

## Files

- `github_repository.py`: GitHub VCS repository (production)
- `gitlab_repository.py`: GitLab VCS repository (stub)
