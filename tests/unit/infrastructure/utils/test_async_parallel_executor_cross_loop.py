from __future__ import annotations

import multiprocessing
import threading
from multiprocessing.queues import Queue

import anyio
import pytest

from prdiffer.infrastructure.utils.parallel.executor import AsyncParallelExecutor


def _run_cross_loop_batch(results: Queue[tuple[tuple[str, ...], tuple[str, ...]]]) -> None:
    executor = AsyncParallelExecutor(max_concurrent=1)
    first_acquired = threading.Event()
    second_waiter_ready = threading.Event()
    batch_results: dict[str, tuple[str, ...]] = {}
    errors: list[Exception] = []

    def run_base_loop() -> None:
        async def process(item: str) -> str:
            first_acquired.set()
            if not await anyio.to_thread.run_sync(second_waiter_ready.wait, 1):
                raise RuntimeError("head loop did not start its semaphore wait")
            return item

        async def run() -> None:
            batch_results["base"] = (await executor.execute_indexed_batch(process, ["base"])).values_in_order

        try:
            anyio.run(run)
        except Exception as error:
            errors.append(error)

    def run_head_loop() -> None:
        async def process(item: str) -> str:
            await anyio.sleep(0)
            return item

        async def run_batch() -> None:
            batch_results["head"] = (await executor.execute_indexed_batch(process, ["head"])).values_in_order

        async def run() -> None:
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(run_batch)
                await anyio.sleep(0)
                await anyio.sleep(0)
                second_waiter_ready.set()

        if not first_acquired.wait(1):
            errors.append(RuntimeError("base loop did not acquire the semaphore"))
            return
        try:
            anyio.run(run)
        except Exception as error:
            errors.append(error)

    base_thread = threading.Thread(target=run_base_loop)
    head_thread = threading.Thread(target=run_head_loop)
    base_thread.start()
    head_thread.start()
    base_thread.join(1)
    head_thread.join(1)

    if errors:
        raise errors[0]
    if base_thread.is_alive() or head_thread.is_alive():
        return
    results.put((batch_results["base"], batch_results["head"]))


@pytest.mark.unit
@pytest.mark.thread_safety
def test_execute_indexed_batch_completes_when_executor_is_reused_across_anyio_loops() -> None:
    context = multiprocessing.get_context("spawn")
    results: Queue[tuple[tuple[str, ...], tuple[str, ...]]] = context.Queue()
    process = context.Process(target=_run_cross_loop_batch, args=(results,))

    # Given: one executor is held by a base-loop batch while a head-loop batch waits.
    process.start()
    try:
        # When: both native threads drive their independent AnyIO loops to completion.
        process.join(2)

        # Then: the child completes and exposes both ordered batch results.
        assert not process.is_alive(), "cross-loop semaphore waiter did not complete"
        assert results.get(timeout=1) == (("base",), ("head",))
    finally:
        if process.is_alive():
            process.terminate()
        process.join(1)
        if process.is_alive():
            process.kill()
            process.join(1)
        results.close()
        results.join_thread()
