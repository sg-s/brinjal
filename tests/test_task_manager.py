"""Tests for TaskManager class"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, AsyncMock
from brinjal.manager import TaskManager
from brinjal.task import ExampleTask


class TestTaskManager:
    """Test cases for TaskManager class"""

    @pytest_asyncio.fixture
    async def task_manager(self):
        """Create a fresh TaskManager instance for each test"""
        manager = TaskManager()
        yield manager
        # Cleanup: stop the manager if it was started
        if manager._worker_task:
            try:
                await manager.stop()
            except asyncio.CancelledError:
                # This is expected when stopping the worker loop
                pass

    @pytest.fixture
    def example_task(self):
        """Create an ExampleTask instance with fast execution"""
        task = ExampleTask()
        task.sleep_time = 0.01  # Use very fast execution for tests
        return task

    @pytest.mark.asyncio
    async def test_task_manager_initialization(self, task_manager):
        """Test TaskManager initializes correctly"""
        assert task_manager.task_queue is not None
        assert task_manager.task_store == {}
        assert task_manager._worker_task is None
        assert task_manager.loop is None

    @pytest.mark.asyncio
    async def test_start_worker_loop(self, task_manager):
        """Test starting the worker loop"""
        await task_manager.start()

        assert task_manager._worker_task is not None
        assert task_manager.loop is not None
        assert not task_manager._worker_task.done()

    @pytest.mark.asyncio
    async def test_stop_worker_loop(self, task_manager):
        """Test stopping the worker loop"""
        await task_manager.start()
        assert task_manager._worker_task is not None

        try:
            await task_manager.stop()
            assert task_manager._worker_task is None
        except asyncio.CancelledError:
            # This is expected when stopping the worker loop
            assert task_manager._worker_task is None

    @pytest.mark.asyncio
    async def test_add_task_to_queue(self, task_manager):
        """Test adding a task to the queue"""
        await task_manager.start()

        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        task_id = await task_manager.add_task_to_queue(task)

        assert task_id == task.task_id
        assert task.loop is not None
        assert task_manager.task_store[task_id] == task

    @pytest.mark.asyncio
    async def test_get_task(self, task_manager):
        """Test retrieving a task by ID"""
        await task_manager.start()

        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        await task_manager.add_task_to_queue(task)

        retrieved_task = task_manager.get_task(task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == task.task_id

    def test_get_nonexistent_task(self):
        """Test retrieving a task that doesn't exist"""
        task_manager = TaskManager()
        task = task_manager.get_task("nonexistent-id")
        assert task is None

    @pytest.mark.asyncio
    async def test_get_all_tasks(self, task_manager):
        """Test getting all tasks"""
        await task_manager.start()

        # Add multiple tasks
        task1 = ExampleTask()
        task1.sleep_time = 0.01  # Fast execution for tests
        task2 = ExampleTask()
        task2.sleep_time = 0.01  # Fast execution for tests
        await task_manager.add_task_to_queue(task1)
        await task_manager.add_task_to_queue(task2)

        all_tasks = task_manager.get_all_tasks()
        assert len(all_tasks) == 2

        task_ids = [t["task_id"] for t in all_tasks]
        assert task1.task_id in task_ids
        assert task2.task_id in task_ids

    @pytest.mark.asyncio
    async def test_task_execution_lifecycle(self, task_manager):
        """Test complete task execution lifecycle"""
        await task_manager.start()

        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        task_id = await task_manager.add_task_to_queue(task)

        # Wait for task to be processed
        await asyncio.sleep(0.1)

        # Check that task was picked up and started
        retrieved_task = task_manager.get_task(task_id)
        assert retrieved_task is not None

        # Wait for task to complete (should be fast with sleep_time=0.01)
        max_wait = 5  # seconds
        wait_time = 0
        while retrieved_task.status != "done" and wait_time < max_wait:
            await asyncio.sleep(0.1)
            wait_time += 0.1
            retrieved_task = task_manager.get_task(task_id)

        assert retrieved_task.status == "done"
        assert retrieved_task.progress == 100

    @pytest.mark.asyncio
    async def test_multiple_tasks_execution(self, task_manager):
        """Test executing multiple tasks simultaneously"""
        await task_manager.start()

        # Create and add multiple tasks
        tasks = [ExampleTask() for _ in range(3)]
        for task in tasks:
            task.sleep_time = 0.01  # Fast execution for tests

        task_ids = []

        for task in tasks:
            task_id = await task_manager.add_task_to_queue(task)
            task_ids.append(task_id)

        # Wait for all tasks to complete (should be fast with sleep_time=0.01)
        max_wait = 10  # seconds
        wait_time = 0

        while wait_time < max_wait:
            all_tasks = task_manager.get_all_tasks()
            completed_tasks = [t for t in all_tasks if t["status"] == "done"]

            if len(completed_tasks) == 3:
                break

            await asyncio.sleep(0.1)
            wait_time += 0.1

        # Verify all tasks completed
        all_tasks = task_manager.get_all_tasks()
        assert len(all_tasks) == 3

        for task_info in all_tasks:
            assert task_info["status"] == "done"
            assert task_info["progress"] == 100

    @pytest.mark.asyncio
    async def test_sse_event_generator(self, task_manager):
        """Test SSE event generator creation"""
        await task_manager.start()

        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        await task_manager.add_task_to_queue(task)

        # Mock request object
        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(return_value=False)

        # Get the event generator
        event_generator = task_manager.get_sse_event_generator(
            task.task_id, mock_request
        )
        assert event_generator is not None

        # Test that it's callable
        assert callable(event_generator)

    @pytest.mark.asyncio
    async def test_sse_event_generator_nonexistent_task(self, task_manager):
        """Test SSE event generator for non-existent task"""
        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(return_value=False)

        event_generator = task_manager.get_sse_event_generator(
            "nonexistent-id", mock_request
        )
        assert event_generator is None

    @pytest.mark.asyncio
    async def test_worker_loop_task_processing(self, task_manager):
        """Test that worker loop processes tasks correctly"""
        await task_manager.start()

        # Create a task that will take some time
        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        await task_manager.add_task_to_queue(task)

        # Wait a bit for the worker to pick up the task
        await asyncio.sleep(0.2)

        # Check that the task is being processed
        retrieved_task = task_manager.get_task(task.task_id)
        assert retrieved_task is not None

        # The task should be running or done by now
        assert retrieved_task.status in ["running", "done"]

    @pytest.mark.asyncio
    async def test_task_queue_management(self, task_manager):
        """Test task queue management"""
        await task_manager.start()

        # Add multiple tasks
        task1 = ExampleTask()
        task1.sleep_time = 0.01  # Fast execution for tests
        task2 = ExampleTask()
        task2.sleep_time = 0.01  # Fast execution for tests
        task3 = ExampleTask()
        task3.sleep_time = 0.01  # Fast execution for tests

        await task_manager.add_task_to_queue(task1)
        await task_manager.add_task_to_queue(task2)
        await task_manager.add_task_to_queue(task3)

        # Check that all tasks are in the store
        assert len(task_manager.task_store) == 3
        assert task1.task_id in task_manager.task_store
        assert task2.task_id in task_manager.task_store
        assert task3.task_id in task_manager.task_store

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, task_manager):
        """Test creating multiple tasks concurrently"""
        await task_manager.start()

        # Create tasks concurrently
        async def create_task():
            task = ExampleTask()
            task.sleep_time = 0.01  # Fast execution for tests
            return await task_manager.add_task_to_queue(task)

        # Create 5 tasks concurrently
        tasks = [create_task() for _ in range(5)]
        task_ids = await asyncio.gather(*tasks)

        # Verify all tasks were created
        assert len(task_ids) == 5
        assert len(task_manager.task_store) == 5

        # All task IDs should be unique
        assert len(set(task_ids)) == 5

    @pytest.mark.asyncio
    async def test_task_manager_restart(self, task_manager):
        """Test stopping and restarting the task manager"""
        await task_manager.start()
        assert task_manager._worker_task is not None

        try:
            await task_manager.stop()
            assert task_manager._worker_task is None
        except asyncio.CancelledError:
            # This is expected when stopping the worker loop
            assert task_manager._worker_task is None

        await task_manager.start()
        assert task_manager._worker_task is not None

    @pytest.mark.asyncio
    async def test_task_progress_updates(self, task_manager):
        """Test that task progress updates are tracked"""
        await task_manager.start()

        task = ExampleTask()
        task.sleep_time = 0.01  # Fast execution for tests
        await task_manager.add_task_to_queue(task)

        # Monitor progress updates
        progress_values = []
        max_wait = 5  # seconds (should be fast with sleep_time=0.01)
        wait_time = 0

        while wait_time < max_wait:
            retrieved_task = task_manager.get_task(task.task_id)
            if retrieved_task and retrieved_task.progress not in progress_values:
                progress_values.append(retrieved_task.progress)

            if retrieved_task and retrieved_task.status == "done":
                break

            await asyncio.sleep(0.1)
            wait_time += 0.1

        # Should have multiple progress values
        assert len(progress_values) > 1
        assert 0 in progress_values  # Should start at 0
        assert 100 in progress_values  # Should end at 100
