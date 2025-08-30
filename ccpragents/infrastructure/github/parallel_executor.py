"""Parallel execution service for batch processing operations."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Any, Optional, Dict
from ccpragents.infrastructure.logging.console_logger import get_logger


class ParallelExecutor:
    """Service for executing operations in parallel using thread pools.

    This class provides utilities for parallel execution of file processing,
    API calls, and other operations that can benefit from concurrent execution.
    """

    def __init__(self,
                 max_workers: int = 4,
                 timeout: Optional[float] = None,
                 logger=None):
        """Initialize the parallel executor.

        Args:
            max_workers: Maximum number of worker threads
            timeout: Timeout for individual operations (optional)
            logger: Logger instance for logging operations
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self._logger = logger or get_logger()

    def execute_batch(self,
                     func: Callable,
                     items: List[Any],
                     *args,
                     **kwargs) -> List[Any]:
        """Execute a function on a list of items in parallel.

        Args:
            func: Function to execute for each item
            items: List of items to process
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results = []
        failed_items = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {}
            for item in items:
                future = executor.submit(func, item, *args, **kwargs)
                future_to_item[future] = item

            # Collect results as they complete
            for future in as_completed(future_to_item, timeout=self.timeout):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    failed_items.append(item)
                    self._logger.error(f"Error processing item {item}: {e}")

        if failed_items:
            self._logger.warning(f"Failed to process {len(failed_items)} items out of {len(items)}")

        return results

    def execute_batch_with_context(self,
                                  func: Callable,
                                  items: List[Any],
                                  context: Dict[str, Any]) -> List[Any]:
        """Execute a function on items with shared context in parallel.

        Args:
            func: Function to execute for each item (should accept item and context)
            items: List of items to process
            context: Shared context dictionary passed to each function call

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results = []
        failed_items = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks with context
            future_to_item = {}
            for item in items:
                future = executor.submit(func, item, context)
                future_to_item[future] = item

            # Collect results as they complete
            for future in as_completed(future_to_item, timeout=self.timeout):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    failed_items.append(item)
                    self._logger.error(f"Error processing item {item}: {e}")

        if failed_items:
            self._logger.warning(f"Failed to process {len(failed_items)} items out of {len(items)}")

        return results

    def execute_mapped_batch(self,
                            func_map: Dict[Any, Callable],
                            items: List[Any],
                            default_func: Optional[Callable] = None,
                            **kwargs) -> List[Any]:
        """Execute different functions based on item type/key in parallel.

        Args:
            func_map: Dictionary mapping item keys/types to functions
            items: List of items to process
            default_func: Default function if item not found in func_map
            **kwargs: Additional keyword arguments for all functions

        Returns:
            List of results from the function calls
        """
        if not items:
            return []

        results = []
        failed_items = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks with appropriate functions
            future_to_item = {}
            for item in items:
                # Determine which function to use
                func = None
                if hasattr(item, '__class__'):
                    func = func_map.get(type(item))
                if func is None:
                    func = func_map.get(item)
                if func is None and default_func:
                    func = default_func

                if func:
                    future = executor.submit(func, item, **kwargs)
                    future_to_item[future] = item
                else:
                    self._logger.warning(f"No function found for item: {item}")

            # Collect results as they complete
            for future in as_completed(future_to_item, timeout=self.timeout):
                item = future_to_item[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                except Exception as e:
                    failed_items.append(item)
                    self._logger.error(f"Error processing item {item}: {e}")

        if failed_items:
            self._logger.warning(f"Failed to process {len(failed_items)} items out of {len(items)}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics.

        Returns:
            Dictionary containing executor statistics
        """
        return {
            'max_workers': self.max_workers,
            'timeout': self.timeout,
        }


def get_parallel_executor(max_workers: int = 4,
                         timeout: Optional[float] = None) -> ParallelExecutor:
    """Get a configured parallel executor instance.

    Args:
        max_workers: Maximum number of worker threads
        timeout: Timeout for individual operations (optional)

    Returns:
        ParallelExecutor: Configured parallel executor instance
    """
    return ParallelExecutor(max_workers=max_workers, timeout=timeout)
