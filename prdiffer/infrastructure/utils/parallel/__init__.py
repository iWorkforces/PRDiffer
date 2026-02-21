"""Parallel execution utilities using anyio task groups.

This package provides native async parallel executor that replaces
ThreadPoolExecutor with anyio's structured concurrency primitives.

Modules:
- executor: AsyncParallelExecutor class for parallel task execution
- results: BatchResult and ErrorStrategy for result handling
- semaphores: Concurrency primitives and helpers
"""

from prdiffer.infrastructure.utils.parallel.executor import (
    AsyncParallelExecutor,
    OPERATIONAL_EXCEPTIONS,
    get_async_parallel_executor,
    create_async_parallel_executor,
)
from prdiffer.infrastructure.utils.parallel.results import (
    BatchResult,
    ErrorStrategy,
)
from prdiffer.infrastructure.utils.parallel.semaphores import (
    SemaphoreManager,
    LockManager,
    create_semaphore,
    create_lock,
)

__all__ = [
    # Executor
    'AsyncParallelExecutor',
    'OPERATIONAL_EXCEPTIONS',
    'get_async_parallel_executor',
    'create_async_parallel_executor',
    # Results
    'BatchResult',
    'ErrorStrategy',
    # Semaphores
    'SemaphoreManager',
    'LockManager',
    'create_semaphore',
    'create_lock',
]
