"""Tests for task pruning functionality."""

import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from brinjal.manager import TaskManager
from brinjal.task import ExampleCPUTask


@pytest_asyncio.fixture
async def task_manager():
    """Create a task manager for testing."""
    manager = TaskManager()
    await manager.start()
    yield manager
    try:
        await manager.stop()
    except asyncio.CancelledError:
        # This is expected when stopping the task manager
        pass


class TestTaskPruning:
    """Test task pruning functionality."""

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        tasks = []
        for i in range(15):  # Create 15 tasks
            task = ExampleCPUTask(name=f"Test Task {i}")
            task.status = "done"
            task.completed_at = datetime.now() - timedelta(minutes=i)
            tasks.append(task)
        return tasks

    @pytest.mark.asyncio
    async def test_pruning_removes_oldest_succeeded_tasks(
        self, task_manager, sample_tasks
    ):
        """Test that pruning removes the oldest succeeded tasks."""
        # Add all tasks to the store
        for task in sample_tasks:
            task_manager.task_store[task.task_id] = task

        # Verify we have 15 tasks
        assert len(task_manager.task_store) == 15

        # Run pruning
        await task_manager._prune_succeeded_tasks()

        # Should only keep 10 tasks (max_succeeded_tasks)
        assert len(task_manager.task_store) == 10

        # Verify the remaining tasks are the newest ones
        remaining_tasks = list(task_manager.task_store.values())
        remaining_tasks.sort(key=lambda t: t.completed_at, reverse=True)

        # Check that we have the 10 newest tasks
        for i, task in enumerate(remaining_tasks):
            expected_minutes_ago = i
            actual_minutes_ago = (
                datetime.now() - task.completed_at
            ).total_seconds() / 60
            assert (
                abs(actual_minutes_ago - expected_minutes_ago) < 1
            )  # Allow 1 minute tolerance

    @pytest.mark.asyncio
    async def test_pruning_keeps_failed_and_queued_tasks(self, task_manager):
        """Test that pruning only affects succeeded tasks."""
        # Create a mix of task statuses
        succeeded_task = ExampleCPUTask(name="Succeeded Task")
        succeeded_task.status = "done"
        succeeded_task.completed_at = datetime.now() - timedelta(minutes=1)

        failed_task = ExampleCPUTask(name="Failed Task")
        failed_task.status = "failed"
        failed_task.completed_at = datetime.now() - timedelta(minutes=1)

        queued_task = ExampleCPUTask(name="Queued Task")
        queued_task.status = "queued"
        queued_task.completed_at = None

        # Add tasks to store
        task_manager.task_store[succeeded_task.task_id] = succeeded_task
        task_manager.task_store[failed_task.task_id] = failed_task
        task_manager.task_store[queued_task.task_id] = queued_task

        # Run pruning
        await task_manager._prune_succeeded_tasks()

        # All tasks should still be there (only 1 succeeded task)
        assert len(task_manager.task_store) == 3
        assert succeeded_task.task_id in task_manager.task_store
        assert failed_task.task_id in task_manager.task_store
        assert queued_task.task_id in task_manager.task_store

    @pytest.mark.asyncio
    async def test_pruning_with_no_succeeded_tasks(self, task_manager):
        """Test pruning when there are no succeeded tasks."""
        # Create only failed and queued tasks
        failed_task = ExampleCPUTask(name="Failed Task")
        failed_task.status = "failed"

        queued_task = ExampleCPUTask(name="Queued Task")
        queued_task.status = "queued"

        task_manager.task_store[failed_task.task_id] = failed_task
        task_manager.task_store[queued_task.task_id] = queued_task

        initial_count = len(task_manager.task_store)

        # Run pruning
        await task_manager._prune_succeeded_tasks()

        # No tasks should be removed
        assert len(task_manager.task_store) == initial_count

    @pytest.mark.asyncio
    async def test_pruning_with_exactly_max_tasks(self, task_manager):
        """Test pruning when we have exactly max_succeeded_tasks."""
        # Create exactly 10 succeeded tasks
        tasks = []
        for i in range(10):
            task = ExampleCPUTask(name=f"Task {i}")
            task.status = "done"
            task.completed_at = datetime.now() - timedelta(minutes=i)
            tasks.append(task)
            task_manager.task_store[task.task_id] = task

        # Run pruning
        await task_manager._prune_succeeded_tasks()

        # All tasks should still be there
        assert len(task_manager.task_store) == 10

    @pytest.mark.asyncio
    async def test_pruning_triggered_on_task_completion(self, task_manager):
        """Test that pruning is triggered when a task completes successfully."""
        # Create 10 succeeded tasks first
        for i in range(10):
            task = ExampleCPUTask(name=f"Old Task {i}")
            task.status = "done"
            task.completed_at = datetime.now() - timedelta(minutes=i + 1)
            task_manager.task_store[task.task_id] = task

        # Create a new task that will complete
        new_task = ExampleCPUTask(name="New Task")
        new_task.status = "done"
        new_task.completed_at = datetime.now()

        # Manually trigger the completion logic (simulating what happens in worker loop)
        task_manager.task_store[new_task.task_id] = new_task
        await task_manager._prune_succeeded_tasks()

        # Should still have 10 tasks (the newest ones)
        assert len(task_manager.task_store) == 10

        # The new task should be among them
        assert new_task.task_id in task_manager.task_store

    @pytest.mark.asyncio
    async def test_pruning_with_tasks_without_completed_at(self, task_manager):
        """Test pruning with succeeded tasks that don't have completed_at set."""
        # Create succeeded tasks without completed_at
        task1 = ExampleCPUTask(name="Task without completed_at")
        task1.status = "done"
        task1.completed_at = None

        # Create succeeded task with completed_at
        task2 = ExampleCPUTask(name="Task with completed_at")
        task2.status = "done"
        task2.completed_at = datetime.now()

        task_manager.task_store[task1.task_id] = task1
        task_manager.task_store[task2.task_id] = task2

        # Run pruning
        await task_manager._prune_succeeded_tasks()

        # Task without completed_at should be removed (not counted as valid succeeded task)
        # Task with completed_at should remain
        assert len(task_manager.task_store) == 1
        assert task2.task_id in task_manager.task_store
        assert task1.task_id not in task_manager.task_store

    def test_max_succeeded_tasks_configuration(self, task_manager):
        """Test that max_succeeded_tasks is configurable."""
        assert task_manager.max_succeeded_tasks == 10

        # Test changing the configuration
        task_manager.max_succeeded_tasks = 5
        assert task_manager.max_succeeded_tasks == 5
