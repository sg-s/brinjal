"""Tests for TaskManager class"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from brinjal.manager import TaskManager
from brinjal.task import ExampleCPUTask, ExampleIOTask


@pytest_asyncio.fixture
async def task_manager():
    """Create a fresh TaskManager instance for each test"""
    manager = TaskManager()
    yield manager
    # Cleanup: stop the manager if it was started
    if manager._worker_tasks:
        try:
            await manager.stop()
        except asyncio.CancelledError:
            # This is expected when stopping the worker loop
            pass


@pytest.fixture
def example_task():
    """Create an ExampleCPUTask instance with fast execution"""
    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Use very fast execution for tests
    return task


@pytest.mark.asyncio
async def test_task_manager_initialization(task_manager):
    """Test TaskManager initializes correctly"""
    assert task_manager.task_queue is not None
    assert task_manager.task_store == {}
    assert task_manager._worker_tasks == []
    assert task_manager.loop is None


@pytest.mark.asyncio
async def test_start_worker_loop(task_manager):
    """Test starting the worker loop"""
    await task_manager.start()

    assert task_manager._worker_tasks
    assert task_manager.loop is not None
    assert len(task_manager._worker_tasks) > 0


@pytest.mark.asyncio
async def test_stop_worker_loop(task_manager):
    """Test stopping the worker loop"""
    await task_manager.start()
    assert task_manager._worker_tasks

    try:
        await task_manager.stop()
        assert task_manager._worker_tasks == []
    except asyncio.CancelledError:
        # This is expected when stopping the worker loop
        assert task_manager._worker_tasks == []


@pytest.mark.asyncio
async def test_add_task_to_queue(task_manager):
    """Test adding a task to the queue"""
    await task_manager.start()

    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Fast execution for tests
    task_id = await task_manager.add_task_to_queue(task)

    assert task_id == task.task_id
    assert task.loop is not None
    assert task_manager.task_store[task_id] == task


@pytest.mark.asyncio
async def test_get_task(task_manager):
    """Test retrieving a task by ID"""
    await task_manager.start()

    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Fast execution for tests
    await task_manager.add_task_to_queue(task)

    retrieved_task = task_manager.get_task(task.task_id)
    assert retrieved_task is not None
    assert retrieved_task.task_id == task.task_id


def test_get_nonexistent_task():
    """Test retrieving a task that doesn't exist"""
    task_manager = TaskManager()
    task = task_manager.get_task("nonexistent-id")
    assert task is None


@pytest.mark.asyncio
async def test_get_all_tasks(task_manager):
    """Test getting all tasks"""
    await task_manager.start()

    # Add multiple tasks
    task1 = ExampleCPUTask()
    task1.sleep_time = 0.01  # Fast execution for tests
    task2 = ExampleCPUTask()
    task2.sleep_time = 0.01  # Fast execution for tests
    await task_manager.add_task_to_queue(task1)
    await task_manager.add_task_to_queue(task2)

    all_tasks = task_manager.get_all_tasks()
    assert len(all_tasks) == 2

    task_ids = [t["task_id"] for t in all_tasks]
    assert task1.task_id in task_ids
    assert task2.task_id in task_ids


@pytest.mark.asyncio
async def test_task_execution_lifecycle(task_manager):
    """Test complete task execution lifecycle"""
    await task_manager.start()

    task = ExampleCPUTask()
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
async def test_multiple_tasks_execution(task_manager):
    """Test executing multiple tasks simultaneously"""
    await task_manager.start()

    # Create and add multiple tasks
    tasks = [ExampleCPUTask() for _ in range(3)]
    for task in tasks:
        task.sleep_time = 0.01  # Fast execution for tests

    task_ids = []

    for task in tasks:
        task_id = await task_manager.add_task_to_queue(task)
        task_ids.append(task_id)

    # Wait for all tasks to complete (each task takes ~4+ seconds, 3 tasks = ~12+ seconds)
    max_wait = 20  # seconds - increased to account for 3 tasks with 3s startup each
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
async def test_sse_event_generator(task_manager):
    """Test SSE event generator creation"""
    await task_manager.start()

    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Fast execution for tests
    await task_manager.add_task_to_queue(task)

    # Mock request object
    mock_request = Mock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    # Get the event generator
    event_generator = task_manager.get_sse_event_generator(task.task_id, mock_request)
    assert event_generator is not None

    # Test that it's callable
    assert callable(event_generator)


@pytest.mark.asyncio
async def test_sse_event_generator_nonexistent_task():
    """Test SSE event generator for non-existent task"""
    mock_request = Mock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    task_manager = TaskManager()
    event_generator = task_manager.get_sse_event_generator(
        "nonexistent-id", mock_request
    )
    assert event_generator is None


@pytest.mark.asyncio
async def test_worker_loop_task_processing(task_manager):
    """Test that worker loop processes tasks correctly"""
    await task_manager.start()

    # Create a task that will take some time
    task = ExampleCPUTask()
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
async def test_task_queue_management(task_manager):
    """Test task queue management"""
    await task_manager.start()

    # Add multiple tasks
    task1 = ExampleCPUTask()
    task1.sleep_time = 0.01  # Fast execution for tests
    task2 = ExampleCPUTask()
    task2.sleep_time = 0.01  # Fast execution for tests
    task3 = ExampleCPUTask()
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
async def test_concurrent_task_creation(task_manager):
    """Test creating multiple tasks concurrently"""
    await task_manager.start()

    # Create tasks concurrently
    async def create_task():
        task = ExampleCPUTask()
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
async def test_task_manager_restart(task_manager):
    """Test stopping and restarting the task manager"""
    await task_manager.start()
    assert task_manager._worker_tasks

    try:
        await task_manager.stop()
        assert task_manager._worker_tasks == []
    except asyncio.CancelledError:
        # This is expected when stopping the worker loop
        assert task_manager._worker_tasks == []

    await task_manager.start()
    assert task_manager._worker_tasks


@pytest.mark.asyncio
async def test_task_progress_updates(task_manager):
    """Test that task progress updates are tracked"""
    await task_manager.start()

    task = ExampleCPUTask()
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


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_empty_criteria(task_manager):
    """Test search with empty criteria returns empty list"""
    result = task_manager.search_tasks_by_attributes({})
    assert result == []


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_no_matches(task_manager):
    """Test search with no matching tasks returns empty list"""
    result = task_manager.search_tasks_by_attributes({"name": "NonExistentTask"})
    assert result == []


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_single_criteria(task_manager):
    """Test search with single criteria"""
    # Create tasks with different names
    task1 = ExampleCPUTask(name="Task A")
    task2 = ExampleCPUTask(name="Task B")
    task3 = ExampleCPUTask(name="Task A")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for tasks with name "Task A"
    result = task_manager.search_tasks_by_attributes({"name": "Task A"})
    assert len(result) == 2
    assert task1.task_id in result
    assert task3.task_id in result
    assert task2.task_id not in result


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_multiple_criteria(task_manager):
    """Test search with multiple criteria (AND logic)"""
    # Create tasks with different attributes
    task1 = ExampleCPUTask(name="Task A", semaphore_name="single")
    task2 = ExampleCPUTask(name="Task A", semaphore_name="multiple")
    task3 = ExampleCPUTask(name="Task B", semaphore_name="single")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for tasks with name "Task A" AND semaphore_name "single"
    result = task_manager.search_tasks_by_attributes(
        {"name": "Task A", "semaphore_name": "single"}
    )
    assert len(result) == 1
    assert task1.task_id in result
    assert task2.task_id not in result
    assert task3.task_id not in result


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_nonexistent_attribute(task_manager):
    """Test search with non-existent attribute returns empty list"""
    task = ExampleCPUTask()
    task_manager.task_store[task.task_id] = task

    # Search for non-existent attribute
    result = task_manager.search_tasks_by_attributes({"nonexistent_attr": "value"})
    assert result == []


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_task_type(task_manager):
    """Test search by task_type (special case)"""
    task1 = ExampleCPUTask()
    task2 = ExampleIOTask()

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2

    # Search for ExampleCPUTask
    result = task_manager.search_tasks_by_attributes({"task_type": "ExampleCPUTask"})
    assert len(result) == 1
    assert task1.task_id in result
    assert task2.task_id not in result

    # Search for ExampleIOTask
    result = task_manager.search_tasks_by_attributes({"task_type": "ExampleIOTask"})
    assert len(result) == 1
    assert task2.task_id in result
    assert task1.task_id not in result


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_task_type_with_other_criteria(task_manager):
    """Test search by task_type combined with other criteria"""
    task1 = ExampleCPUTask(name="CPU Task", semaphore_name="single")
    task2 = ExampleCPUTask(name="Another CPU Task", semaphore_name="single")
    task3 = ExampleIOTask(semaphore_name="multiple")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for ExampleCPUTask with semaphore_name "single"
    result = task_manager.search_tasks_by_attributes(
        {"task_type": "ExampleCPUTask", "semaphore_name": "single"}
    )
    assert len(result) == 2
    assert task1.task_id in result
    assert task2.task_id in result
    assert task3.task_id not in result


@pytest.mark.asyncio
async def test_search_tasks_by_attributes_mixed_task_types(task_manager):
    """Test search across different task types with common attributes"""
    task1 = ExampleCPUTask(name="Common Name", semaphore_name="single")
    task2 = ExampleIOTask(semaphore_name="multiple")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2

    # Search for tasks with semaphore_name "single" (should find only CPU task)
    result = task_manager.search_tasks_by_attributes({"semaphore_name": "single"})
    assert len(result) == 1
    assert task1.task_id in result
    assert task2.task_id not in result

    # Search for tasks with semaphore_name "multiple" (should find only IO task)
    result = task_manager.search_tasks_by_attributes({"semaphore_name": "multiple"})
    assert len(result) == 1
    assert task2.task_id in result
    assert task1.task_id not in result
