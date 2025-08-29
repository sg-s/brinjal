"""Tests for API router endpoints"""

import pytest
from fastapi.testclient import TestClient

from brinjal.api.router import router
from brinjal.manager import task_manager
from brinjal.task import ExampleCPUTask, ExampleIOTask

# Create a test client
client = TestClient(router)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown for each test"""
    # Clear the task store before each test
    task_manager.task_store.clear()
    yield
    # Clear the task store after each test
    task_manager.task_store.clear()


def test_search_tasks_empty_store():
    """Test search when no tasks exist"""
    response = client.post("/search", json={})
    assert response.status_code == 200
    assert response.json() == {"task_ids": []}


def test_search_tasks_no_criteria():
    """Test search with empty criteria"""
    response = client.post("/search", json={})
    assert response.status_code == 200
    assert response.json() == {"task_ids": []}


def test_search_tasks_by_name():
    """Test search by task name"""
    # Create tasks with different names
    task1 = ExampleCPUTask(name="Task A")
    task2 = ExampleCPUTask(name="Task B")
    task3 = ExampleCPUTask(name="Task A")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for tasks with name "Task A"
    response = client.post("/search", json={"name": "Task A"})
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 2
    assert task1.task_id in result["task_ids"]
    assert task3.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]


def test_search_tasks_by_status():
    """Test search by task status"""
    # Create tasks with different statuses
    task1 = ExampleCPUTask()
    task1.status = "running"
    task2 = ExampleCPUTask()
    task2.status = "done"
    task3 = ExampleCPUTask()
    task3.status = "running"

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for running tasks
    response = client.post("/search", json={"status": "running"})
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 2
    assert task1.task_id in result["task_ids"]
    assert task3.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]


def test_search_tasks_by_task_type():
    """Test search by task type"""
    # Create different types of tasks
    task1 = ExampleCPUTask()
    task2 = ExampleIOTask()
    task3 = ExampleCPUTask()

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for ExampleCPUTask
    response = client.post("/search", json={"task_type": "ExampleCPUTask"})
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 2
    assert task1.task_id in result["task_ids"]
    assert task3.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]


def test_search_tasks_multiple_criteria():
    """Test search with multiple criteria (AND logic)"""
    # Create tasks with different attributes
    task1 = ExampleCPUTask(name="Task A", semaphore_name="single")
    task2 = ExampleCPUTask(name="Task A", semaphore_name="multiple")
    task3 = ExampleCPUTask(name="Task B", semaphore_name="single")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3

    # Search for tasks with name "Task A" AND semaphore_name "single"
    response = client.post(
        "/search", json={"name": "Task A", "semaphore_name": "single"}
    )
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 1
    assert task1.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]
    assert task3.task_id not in result["task_ids"]


def test_search_tasks_nonexistent_attribute():
    """Test search with non-existent attribute returns empty list"""
    task = ExampleCPUTask()
    task_manager.task_store[task.task_id] = task

    # Search for non-existent attribute
    response = client.post("/search", json={"nonexistent_attr": "value"})
    assert response.status_code == 200
    assert response.json() == {"task_ids": []}


def test_search_tasks_no_matches():
    """Test search with no matching tasks returns empty list"""
    task = ExampleCPUTask(name="Task A")
    task_manager.task_store[task.task_id] = task

    # Search for different name
    response = client.post("/search", json={"name": "Task B"})
    assert response.status_code == 200
    assert response.json() == {"task_ids": []}


def test_search_tasks_mixed_task_types():
    """Test search across different task types with common attributes"""
    task1 = ExampleCPUTask(name="Common Name", semaphore_name="single")
    task2 = ExampleIOTask(semaphore_name="multiple")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2

    # Search for tasks with semaphore_name "single" (should find only CPU task)
    response = client.post("/search", json={"semaphore_name": "single"})
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 1
    assert task1.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]

    # Search for tasks with semaphore_name "multiple" (should find only IO task)
    response = client.post("/search", json={"semaphore_name": "multiple"})
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 1
    assert task2.task_id in result["task_ids"]
    assert task1.task_id not in result["task_ids"]


def test_search_tasks_complex_criteria():
    """Test search with complex criteria combinations"""
    # Create tasks with various attributes
    task1 = ExampleCPUTask(name="CPU Task", semaphore_name="single", sleep_time=0.1)
    task2 = ExampleCPUTask(name="CPU Task", semaphore_name="single", sleep_time=0.2)
    task3 = ExampleCPUTask(name="CPU Task", semaphore_name="multiple", sleep_time=0.1)
    task4 = ExampleIOTask(semaphore_name="multiple", progress_file="test.txt")

    task_manager.task_store[task1.task_id] = task1
    task_manager.task_store[task2.task_id] = task2
    task_manager.task_store[task3.task_id] = task3
    task_manager.task_store[task4.task_id] = task4

    # Search for CPU tasks with single semaphore and sleep_time 0.1
    response = client.post(
        "/search",
        json={
            "task_type": "ExampleCPUTask",
            "semaphore_name": "single",
            "sleep_time": 0.1,
        },
    )
    assert response.status_code == 200

    result = response.json()
    assert len(result["task_ids"]) == 1
    assert task1.task_id in result["task_ids"]
    assert task2.task_id not in result["task_ids"]  # Different sleep_time
    assert task3.task_id not in result["task_ids"]  # Different semaphore_name
    assert task4.task_id not in result["task_ids"]  # Different task type


def test_example_cpu_task_with_name():
    """Test the example CPU task endpoint with custom name"""
    response = client.post("/example_cpu_task", params={"name": "Custom Task Name"})
    assert response.status_code == 200

    result = response.json()
    assert "task_id" in result
    assert len(result["task_id"]) > 0

    # Verify the task was created with the custom name
    task_id = result["task_id"]
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.name == "Custom Task Name"


def test_example_cpu_task_default_name():
    """Test the example CPU task endpoint with default name"""
    response = client.post("/example_cpu_task")
    assert response.status_code == 200

    result = response.json()
    assert "task_id" in result
    assert len(result["task_id"]) > 0

    # Verify the task was created with the default name
    task_id = result["task_id"]
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.name == "Example Task"
