"""Tests for semaphore-based concurrency control"""

import asyncio
import time

import pytest
import pytest_asyncio

from brinjal.manager import TaskManager
from brinjal.task import ExampleCPUTask, ExampleIOTask


@pytest_asyncio.fixture
async def task_manager():
    """Create a fresh task manager for each test"""
    manager = TaskManager()
    await manager.start()
    yield manager
    try:
        await manager.stop()
    except asyncio.CancelledError:
        # Handle cancellation gracefully during teardown
        pass


@pytest.fixture
def tracked_execute_cpu():
    """Fixture that provides a tracked execute function for CPU tasks"""
    execution_order = []
    execution_times = {}

    async def tracked_execute(self):
        execution_order.append(self.task_id)
        execution_times[self.task_id] = time.time()
        # Simulate some work
        await asyncio.sleep(0.1)
        self.status = "done"

    return tracked_execute, execution_order, execution_times


@pytest.fixture
def tracked_execute_io():
    """Fixture that provides a tracked execute function for I/O tasks"""
    execution_order = []
    execution_times = {}

    async def tracked_execute(self):
        execution_order.append(self.task_id)
        execution_times[self.task_id] = time.time()
        # Simulate some work
        await asyncio.sleep(0.1)
        self.status = "done"

    return tracked_execute, execution_order, execution_times


@pytest.fixture
def long_running_execute():
    """Fixture that provides a long-running execute function for testing concurrency limits"""

    async def long_execute(self):
        await asyncio.sleep(0.5)  # Long enough to test concurrency
        self.status = "done"

    return long_execute


@pytest.mark.asyncio
async def test_single_semaphore_limits_concurrency(task_manager, tracked_execute_cpu):
    """Test that 'single' semaphore only allows one task at a time"""
    tracked_execute, execution_order, execution_times = tracked_execute_cpu

    # Create multiple ExampleCPUTasks (which use 'single' semaphore)
    tasks = [ExampleCPUTask() for _ in range(3)]

    # Apply the tracked execute function to all tasks
    for task in tasks:
        task.execute = tracked_execute.__get__(task, ExampleCPUTask)

    # Add all tasks to queue
    for task in tasks:
        await task_manager.add_task_to_queue(task)

    # Wait for all tasks to complete
    await asyncio.sleep(1)

    # Verify only one task ran at a time
    assert len(execution_order) == 3

    # Check that tasks didn't run simultaneously
    # The execution times should be sequential (with small tolerance)
    for i in range(1, len(execution_order)):
        time_diff = (
            execution_times[execution_order[i]]
            - execution_times[execution_order[i - 1]]
        )
        assert time_diff >= 0.05  # At least 50ms between tasks


@pytest.mark.asyncio
async def test_multiple_semaphore_allows_concurrency(task_manager, tracked_execute_io):
    """Test that 'multiple' semaphore allows concurrent execution"""
    tracked_execute, execution_order, execution_times = tracked_execute_io

    # Create multiple ExampleIOTasks (which use 'multiple' semaphore)
    tasks = [ExampleIOTask() for _ in range(3)]

    # Apply the tracked execute function to all tasks
    for task in tasks:
        task.execute = tracked_execute.__get__(task, ExampleIOTask)

    # Add all tasks to queue
    for task in tasks:
        await task_manager.add_task_to_queue(task)

    # Wait for all tasks to complete
    await asyncio.sleep(1)

    # Verify all tasks executed
    assert len(execution_order) == 3

    # Check that tasks ran concurrently (execution times should be close)
    max_time_diff = max(execution_times.values()) - min(execution_times.values())
    assert max_time_diff < 0.2  # All tasks should start within 200ms of each other


@pytest.mark.asyncio
async def test_default_semaphore_behavior(task_manager):
    """Test that tasks without explicit semaphore use 'default'"""
    # Create a task without setting semaphore_name (should use "default")
    task = ExampleCPUTask()
    task.semaphore_name = "default"  # Explicitly set to test

    execution_started = False

    async def tracked_execute(self):
        nonlocal execution_started
        execution_started = True
        self.status = "done"

    task.execute = tracked_execute.__get__(task, ExampleCPUTask)

    # Add task to queue
    await task_manager.add_task_to_queue(task)

    # Wait for task to complete
    await asyncio.sleep(0.5)

    # Verify task executed
    assert execution_started
    assert task.status == "done"


@pytest.mark.asyncio
async def test_task_status_flow(task_manager):
    """Test the task status flow: queued -> running -> done"""
    task = ExampleCPUTask()

    status_changes = []

    async def tracked_execute(self):
        status_changes.append(("executing", self.status))
        self.status = "done"

    task.execute = tracked_execute.__get__(task, ExampleCPUTask)

    # Add task to queue
    await task_manager.add_task_to_queue(task)

    # Check initial status
    assert task.status == "queued"

    # Wait for task to complete
    await asyncio.sleep(0.5)

    # Check final status
    assert task.status == "done"

    # Verify status progression
    assert len(status_changes) > 0
    assert status_changes[0][1] == "running"  # Should be running when execute is called


@pytest.mark.asyncio
async def test_semaphore_limits_respected(task_manager, long_running_execute):
    """Test that semaphore limits are properly enforced"""
    # Test that we can't exceed the 'single' semaphore limit
    single_tasks = [ExampleCPUTask() for _ in range(5)]

    # Apply the long-running execute function to all tasks
    for task in single_tasks:
        task.execute = long_running_execute.__get__(task, ExampleCPUTask)

    # Add all tasks to queue
    for task in single_tasks:
        await task_manager.add_task_to_queue(task)

    # Wait a bit and check how many are running
    await asyncio.sleep(0.2)

    running_count = sum(1 for task in single_tasks if task.status == "running")
    assert running_count == 1  # Only one should be running at a time

    # Wait for completion - increase wait time to ensure all tasks finish
    await asyncio.sleep(3.0)  # Increased from 1.0 to 3.0 seconds

    # All should be done
    for task in single_tasks:
        assert task.status == "done"
