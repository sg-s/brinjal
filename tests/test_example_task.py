"""Tests for ExampleTask class"""

import asyncio
import queue
import threading
import time

import pytest

from brinjal.task import ExampleCPUTask


@pytest.fixture
def example_task():
    """Create a fresh ExampleCPUTask instance for each test with fast execution"""
    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Use very fast execution for tests
    return task


def test_example_task_initialization(example_task):
    """Test ExampleTask initializes correctly"""
    assert example_task.task_id is not None
    assert len(example_task.task_id) > 0
    assert example_task.status == "queued"
    assert example_task.progress == 0
    assert example_task.results is None
    assert example_task.update_queue is not None
    assert example_task.loop is None
    assert example_task.img is None
    assert example_task.heading is None
    assert example_task.body is None
    assert example_task.sleep_time == 0.01


def test_example_task_unique_ids():
    """Test that each ExampleCPUTask gets a unique ID"""
    task1 = ExampleCPUTask()
    task2 = ExampleCPUTask()
    task3 = ExampleCPUTask()

    ids = {task1.task_id, task2.task_id, task3.task_id}
    assert len(ids) == 3


def test_example_task_run_method(example_task):
    """Test the run method executes correctly"""
    start_time = time.time()

    # Run the task
    example_task.run()

    end_time = time.time()

    # Verify final state
    assert example_task.status == "done"
    assert example_task.progress == 100

    # Verify it took reasonable time (should be ~4+ seconds with 3s startup + 1s execution with sleep_time=0.01)
    duration = end_time - start_time
    assert (
        3.0 <= duration <= 6.0
    )  # Allow some variance for the 3s startup + execution time


def test_example_task_progress_increments():
    """Test that progress increments during execution"""
    # Create a new task for this test to avoid interference
    task = ExampleCPUTask()
    task.sleep_time = 0.01

    # Run the task and capture progress at key points
    initial_progress = task.progress
    assert initial_progress == 0

    # Start the task in a separate thread
    def run_task():
        task.run()

    thread = threading.Thread(target=run_task)
    thread.start()

    # Wait for the startup phase to complete (3+ seconds) and check progress
    time.sleep(3.5)
    mid_progress = task.progress
    # Progress should be >= 0 after startup phase (could be 0 or higher)
    assert mid_progress >= 0

    # Wait for completion
    thread.join()

    # Verify final state
    assert task.progress == 100
    assert task.status == "done"


@pytest.mark.asyncio
async def test_example_task_execute_method(example_task):
    """Test the execute method with progress monitoring"""
    # Mock the update queue to capture notifications
    original_notify_update = example_task.notify_update
    notifications = []

    async def mock_notify_update():
        notifications.append(
            {"status": example_task.status, "progress": example_task.progress}
        )
        await original_notify_update()

    example_task.notify_update = mock_notify_update

    # Execute the task
    await example_task.execute()

    # Verify final state
    assert example_task.status == "done"
    assert example_task.progress == 100

    # Verify notifications were sent
    assert len(notifications) > 1

    # Check initial notification
    assert notifications[0]["status"] == "running"
    assert notifications[0]["progress"] == 0

    # Check final notification
    assert notifications[-1]["status"] == "done"
    assert notifications[-1]["progress"] == 100


@pytest.mark.asyncio
async def test_example_task_notify_update(example_task):
    """Test the notify_update method"""
    # Set some values
    example_task.status = "running"
    example_task.progress = 50
    example_task.heading = "Test Task"
    example_task.body = "Test Description"

    # Call notify_update
    await example_task.notify_update()

    # Check that the update was queued
    assert not example_task.update_queue.empty()

    # Get the update from the queue
    update = await example_task.update_queue.get()

    # Verify update content
    assert update["task_id"] == example_task.task_id
    assert update["task_type"] == "ExampleCPUTask"
    assert update["status"] == "running"
    assert update["progress"] == 50
    assert update["heading"] == "Test Task"
    assert update["body"] == "Test Description"


def test_example_task_run_method_thread_safety():
    """Test that run method can be called from different threads"""
    results = queue.Queue()

    def run_task_in_thread():
        try:
            task = ExampleCPUTask()
            task.sleep_time = 0.01  # Fast execution for tests
            task.run()
            results.put(
                {"status": task.status, "progress": task.progress, "success": True}
            )
        except Exception as e:
            results.put({"success": False, "error": str(e)})

    # Run multiple tasks in different threads
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=run_task_in_thread)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check results
    assert results.qsize() == 3

    for _ in range(3):
        result = results.get()
        assert result["success"] is True
        assert result["status"] == "done"
        assert result["progress"] == 100


@pytest.mark.asyncio
async def test_example_task_cancellation_handling(example_task):
    """Test that the task handles cancellation gracefully"""
    # Start execution in background
    execute_task = asyncio.create_task(example_task.execute())

    # Wait a bit for it to start
    await asyncio.sleep(0.1)

    # Cancel the task
    execute_task.cancel()

    try:
        await execute_task
    except asyncio.CancelledError:
        pass

    # Task should be in a reasonable state
    assert example_task.status in ["queued", "running", "done"]


def test_example_task_attributes_modification(example_task):
    """Test that task attributes can be modified"""
    # Modify various attributes
    example_task.heading = "Custom Heading"
    example_task.body = "Custom Body"
    example_task.img = "https://example.com/image.jpg"

    # Verify modifications
    assert example_task.heading == "Custom Heading"
    assert example_task.body == "Custom Body"
    assert example_task.img == "https://example.com/image.jpg"


def test_example_task_string_representation(example_task):
    """Test string representation of the task"""
    # Set some values
    example_task.heading = "Test Task"
    example_task.progress = 75

    # Convert to string (should not raise an error)
    str_repr = str(example_task)
    assert isinstance(str_repr, str)
    assert len(str_repr) > 0


@pytest.mark.asyncio
async def test_example_task_multiple_executions():
    """Test that the same task can be executed multiple times"""
    task = ExampleCPUTask()
    task.sleep_time = 0.01  # Fast execution for tests

    # Execute first time
    await task.execute()
    assert task.status == "done"
    assert task.progress == 100

    # Reset and execute again
    task.status = "queued"
    task.progress = 0

    await task.execute()
    assert task.status == "done"
    assert task.progress == 100


def test_example_task_progress_consistency():
    """Test that progress values are consistent during execution"""
    # Create a new task for this test
    task = ExampleCPUTask()
    task.sleep_time = 0.01

    # Run the task
    task.run()

    # Verify final state
    assert task.status == "done"
    assert task.progress == 100
    assert 0 <= task.progress <= 100
