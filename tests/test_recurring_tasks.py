"""Tests for recurring task functionality"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from brinjal.manager import RecurringTaskInfo, TaskManager
from brinjal.task import ExampleCPUTask, Task


def test_recurring_task_info_creation():
    """Test creating a RecurringTaskInfo instance"""
    template_task = ExampleCPUTask()
    recurring_info = RecurringTaskInfo(
        cron_expression="*/5 * * * *", template_task=template_task, max_concurrent=2
    )

    assert recurring_info.cron_expression == "*/5 * * * *"
    assert recurring_info.template_task == template_task
    assert recurring_info.max_concurrent == 2
    assert recurring_info.enabled is True
    assert recurring_info.consecutive_failures == 0
    assert recurring_info.total_runs == 0
    assert recurring_info.total_failures == 0
    assert recurring_info.recurring_id is not None
    assert recurring_info.created_at is not None


@pytest.fixture
def task_manager():
    """Create a fresh TaskManager instance for each test"""
    return TaskManager()


@pytest.fixture
def example_task():
    """Create an example task for testing"""
    return ExampleCPUTask(sleep_time=0.01)  # Fast for testing


def test_add_recurring_task(task_manager, example_task):
    """Test adding a recurring task"""
    recurring_id = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *",
            template_task=example_task,
            max_concurrent=1,
        )
    )

    assert recurring_id is not None
    assert recurring_id in task_manager.recurring_tasks

    recurring_info = task_manager.recurring_tasks[recurring_id]
    assert recurring_info.cron_expression == "*/5 * * * *"
    assert recurring_info.template_task == example_task
    assert recurring_info.max_concurrent == 1
    assert recurring_info.enabled is True


def test_get_recurring_task(task_manager, example_task):
    """Test retrieving a recurring task by ID"""
    recurring_id = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *", template_task=example_task
        )
    )

    retrieved_info = task_manager.get_recurring_task(recurring_id)
    assert retrieved_info is not None
    assert retrieved_info.recurring_id == recurring_id

    # Test getting non-existent recurring task
    assert task_manager.get_recurring_task("non-existent") is None


def test_get_all_recurring_tasks(task_manager, example_task):
    """Test getting all recurring tasks"""
    # Add multiple recurring tasks
    recurring_id_1 = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *", template_task=example_task
        )
    )

    recurring_id_2 = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="0 * * * *", template_task=example_task
        )
    )

    all_recurring = task_manager.get_all_recurring_tasks()
    assert len(all_recurring) == 2

    recurring_ids = [info.recurring_id for info in all_recurring]
    assert recurring_id_1 in recurring_ids
    assert recurring_id_2 in recurring_ids


def test_disable_enable_recurring_task(task_manager, example_task):
    """Test disabling and enabling recurring tasks"""
    recurring_id = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *", template_task=example_task
        )
    )

    # Initially enabled
    assert task_manager.recurring_tasks[recurring_id].enabled is True

    # Disable
    assert task_manager.disable_recurring_task(recurring_id) is True
    assert task_manager.recurring_tasks[recurring_id].enabled is False

    # Enable
    assert task_manager.enable_recurring_task(recurring_id) is True
    assert task_manager.recurring_tasks[recurring_id].enabled is True

    # Test with non-existent ID
    assert task_manager.disable_recurring_task("non-existent") is False
    assert task_manager.enable_recurring_task("non-existent") is False


def test_remove_recurring_task(task_manager, example_task):
    """Test removing recurring tasks"""
    recurring_id = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *", template_task=example_task
        )
    )

    assert recurring_id in task_manager.recurring_tasks

    # Remove
    assert task_manager.remove_recurring_task(recurring_id) is True
    assert recurring_id not in task_manager.recurring_tasks

    # Test removing non-existent
    assert task_manager.remove_recurring_task("non-existent") is False


def test_clone_task(task_manager, example_task):
    """Test task cloning functionality"""
    # Set some custom attributes
    example_task.heading = "Test Task"
    example_task.body = "Test Description"

    cloned_task = task_manager._clone_task(example_task, "parent-123")

    # Check that attributes are copied
    assert cloned_task.heading == "Test Task"
    assert cloned_task.body == "Test Description"
    assert cloned_task.sleep_time == example_task.sleep_time

    # Check that new task_id and parent_id are set
    assert cloned_task.task_id != example_task.task_id
    assert cloned_task.parent_id == "parent-123"

    # Check that update_queue is fresh
    assert cloned_task.update_queue != example_task.update_queue


def test_can_run_recurring_task(task_manager, example_task):
    """Test concurrent execution limits"""
    recurring_id = asyncio.run(
        task_manager.add_recurring_task(
            cron_expression="*/5 * * * *",
            template_task=example_task,
            max_concurrent=2,
        )
    )

    recurring_info = task_manager.recurring_tasks[recurring_id]

    # Initially can run
    assert task_manager._can_run_recurring_task(recurring_id, recurring_info) is True

    # Disable and check
    task_manager.disable_recurring_task(recurring_id)
    assert task_manager._can_run_recurring_task(recurring_id, recurring_info) is False

    # Re-enable
    task_manager.enable_recurring_task(recurring_id)
    assert task_manager._can_run_recurring_task(recurring_id, recurring_info) is True


def test_calculate_next_run(task_manager):
    """Test next run time calculation"""
    # This test requires croniter to be installed
    try:
        next_run = task_manager._calculate_next_run("*/5 * * * *")
        assert isinstance(next_run, datetime)
    except ImportError:
        pytest.skip("croniter not available")


def test_calculate_next_run_missing_croniter(task_manager):
    """Test error handling when croniter is not installed"""
    # Mock the import to simulate croniter not being available
    with patch.dict("sys.modules", {"croniter": None}):
        with pytest.raises(
            ModuleNotFoundError, match="import of croniter halted; None in sys.modules"
        ):
            task_manager._calculate_next_run("*/5 * * * *")


def test_task_with_parent_id():
    """Test creating a task with a parent ID"""
    task = ExampleCPUTask(parent_id="parent-123")

    assert task.parent_id == "parent-123"
    assert task.task_id is not None
    assert task.task_id != "parent-123"


def test_task_without_parent_id():
    """Test creating a task without a parent ID"""
    task = ExampleCPUTask()

    assert task.parent_id is None
    assert task.task_id is not None


def test_task_update_includes_parent_id(example_task):
    """Test that task updates include parent_id"""
    example_task.parent_id = "parent-123"

    # Mock the update queue with AsyncMock
    example_task.update_queue = AsyncMock()
    example_task.update_queue.put = AsyncMock()

    asyncio.run(example_task.notify_update())

    # Check that the update was sent with parent_id
    call_args = example_task.update_queue.put.call_args[0][0]
    assert call_args["parent_id"] == "parent-123"
