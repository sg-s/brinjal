"""Tests for task registry and auto-route generation."""

from dataclasses import dataclass
from typing import Optional

import pytest

from brinjal.registry import EXCLUDED_FIELDS, TaskRegistry, registry
from brinjal.task import ExampleCPUTask, Task


def test_registry_register_task():
    """Test registering a task class"""
    test_registry = TaskRegistry()

    test_registry.register(ExampleCPUTask)
    assert "ExampleCPUTask" in test_registry.get_all_tasks()
    assert test_registry.get_task_class("ExampleCPUTask") == ExampleCPUTask


def test_registry_register_invalid_class():
    """Test that registering a non-Task class raises an error"""
    test_registry = TaskRegistry()

    class NotATask:
        pass

    with pytest.raises(ValueError, match="must be a subclass of Task"):
        test_registry.register(NotATask)


def test_registry_register_non_dataclass():
    """Test that registering a non-Task class raises an error"""
    test_registry = TaskRegistry()

    # Create a class that is not a Task subclass
    class NotATaskClass:
        pass

    # This should fail because it's not a Task subclass
    with pytest.raises(ValueError, match="must be a subclass of Task"):
        test_registry.register(NotATaskClass)


def test_registry_get_route_params():
    """Test extracting route parameters from a task class"""
    test_registry = TaskRegistry()
    params = test_registry.get_route_params(ExampleCPUTask)

    # Should include user-configurable fields
    param_names = [p["name"] for p in params]
    assert "name" in param_names
    assert "sleep_time" in param_names
    assert "failure_probability" in param_names

    # Should exclude internal fields
    assert "task_id" not in param_names
    assert "status" not in param_names
    assert "progress" not in param_names
    assert "update_queue" not in param_names


def test_registry_get_route_params_excludes_internal_fields():
    """Test that internal fields are excluded from route parameters"""
    test_registry = TaskRegistry()
    params = test_registry.get_route_params(ExampleCPUTask)

    param_names = [p["name"] for p in params]

    # Check all excluded fields are not present
    for excluded_field in EXCLUDED_FIELDS:
        assert excluded_field not in param_names


def test_registry_get_route_params_required_fields():
    """Test that required vs optional fields are correctly identified"""
    test_registry = TaskRegistry()
    params = test_registry.get_route_params(ExampleCPUTask)

    # Find the name parameter
    name_param = next(p for p in params if p["name"] == "name")
    # name has a default value, so it should not be required
    assert name_param["required"] is False
    assert name_param["default"] == "Example Task"


def test_registry_class_name_to_route():
    """Test converting class names to route paths"""
    assert TaskRegistry.class_name_to_route("ExampleCPUTask") == "/example_cpu_task"
    assert TaskRegistry.class_name_to_route("MyCustomTask") == "/my_custom_task"
    assert TaskRegistry.class_name_to_route("Task") == "/task"
    assert TaskRegistry.class_name_to_route("HTTPRequestTask") == "/http_request_task"


def test_registry_global_instance():
    """Test that the global registry instance works"""
    # Register a task
    registry.register(ExampleCPUTask)

    # Should be able to retrieve it
    assert "ExampleCPUTask" in registry.get_all_tasks()
    assert registry.get_task_class("ExampleCPUTask") == ExampleCPUTask


def test_registry_get_task_class_not_found():
    """Test that getting a non-existent task raises an error"""
    test_registry = TaskRegistry()

    with pytest.raises(ValueError, match="is not registered"):
        test_registry.get_task_class("NonExistentTask")


def test_registry_get_route_params_empty_task():
    """Test getting route params for a task with only excluded fields"""
    test_registry = TaskRegistry()

    @dataclass
    class MinimalTask(Task):
        """A task with no user-configurable fields"""

        pass

    params = test_registry.get_route_params(MinimalTask)
    # Task base class has some configurable fields like img, heading, body, etc.
    # So we check that internal fields are excluded, not that the list is empty
    param_names = [p["name"] for p in params]

    # Verify internal fields are excluded
    assert "task_id" not in param_names
    assert "status" not in param_names
    assert "progress" not in param_names
    assert "update_queue" not in param_names


def test_registry_get_route_params_custom_task():
    """Test getting route params for a custom task"""
    test_registry = TaskRegistry()

    @dataclass
    class CustomTask(Task):
        # Since Task base class has fields with defaults, we can only add
        # fields with defaults in subclasses (or use kw_only, but that's more complex)
        custom_field: str = "default"
        optional_field: Optional[str] = None
        numeric_field: float = 42.0

    params = test_registry.get_route_params(CustomTask)
    param_dict = {p["name"]: p for p in params}

    # Check custom fields are included
    assert "custom_field" in param_dict
    assert "optional_field" in param_dict
    assert "numeric_field" in param_dict

    # Check that fields are marked as optional (have defaults)
    assert param_dict["custom_field"]["required"] is False
    assert param_dict["optional_field"]["required"] is False
    assert param_dict["numeric_field"]["required"] is False
    assert param_dict["custom_field"]["default"] == "default"
    assert abs(param_dict["numeric_field"]["default"] - 42.0) < 1e-9
