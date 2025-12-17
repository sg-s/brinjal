"""Task registry for auto-discovery and route generation."""

import re
from dataclasses import MISSING, fields, is_dataclass
from typing import Dict, List, Type, TypeVar

from .task import Task

T = TypeVar("T", bound=Task)

# Fields from the base Task class that should be excluded from route parameters
EXCLUDED_FIELDS = {
    "task_id",  # Auto-generated
    "parent_id",  # Internal
    "status",  # Internal state
    "progress",  # Internal state
    "update_queue",  # Internal
    "loop",  # Internal
    "started_at",  # Internal
    "completed_at",  # Internal
    "error_message",  # Internal
    "error_type",  # Internal
    "error_traceback",  # Internal
    "results",  # Internal
}


class TaskRegistry:
    """Registry for Task subclasses that enables automatic route generation."""

    def __init__(self):
        self._tasks: Dict[str, Type[Task]] = {}

    def register(self, task_class: Type[T]) -> Type[T]:
        """Register a Task subclass.

        Args:
            task_class: The Task subclass to register

        Returns:
            The same task class (for use as a decorator)

        Example:
            @registry.register
            class MyTask(Task):
                ...
        """
        if not issubclass(task_class, Task):
            raise ValueError(f"{task_class.__name__} must be a subclass of Task")
        if not is_dataclass(task_class):
            raise ValueError(f"{task_class.__name__} must be a dataclass")

        task_name = task_class.__name__
        self._tasks[task_name] = task_class
        return task_class

    def get_task_class(self, task_name: str) -> Type[Task]:
        """Get a registered task class by name."""
        if task_name not in self._tasks:
            raise ValueError(f"Task {task_name} is not registered")
        return self._tasks[task_name]

    def get_all_tasks(self) -> Dict[str, Type[Task]]:
        """Get all registered tasks."""
        return self._tasks.copy()

    def get_route_params(self, task_class: Type[Task]) -> List[Dict]:
        """Extract route parameters from a Task class's dataclass fields.

        Returns a list of dictionaries containing field information for route generation.
        Excludes internal fields that shouldn't be user-configurable.

        Args:
            task_class: The Task subclass to extract parameters from

        Returns:
            List of dictionaries with keys: name, type, default, required
        """
        params = []
        task_fields = fields(task_class)

        for field_info in task_fields:
            field_name = field_info.name

            # Skip excluded fields
            if field_name in EXCLUDED_FIELDS:
                continue

            # Get field type
            field_type = field_info.type

            # Determine if field has a default value
            has_default = field_info.default is not MISSING
            has_default_factory = field_info.default_factory is not MISSING

            # Handle default values
            default_value = None
            if has_default:
                default_value = field_info.default
            elif has_default_factory:
                # For default_factory, we can't use the factory value directly
                # We'll mark it as optional (None default) and let the dataclass handle it
                default_value = None

            params.append(
                {
                    "name": field_name,
                    "type": field_type,
                    "default": default_value,
                    "required": not (has_default or has_default_factory),
                }
            )

        return params

    @staticmethod
    def class_name_to_route(class_name: str) -> str:
        """Convert a class name to a route path.

        Converts CamelCase to snake_case and adds a leading slash.
        Handles consecutive uppercase letters correctly.

        Examples:
            ExampleCPUTask -> /example_cpu_task
            MyCustomTask -> /my_custom_task
            HTTPRequestTask -> /http_request_task
        """
        # First, insert underscore before uppercase that follows lowercase
        result = re.sub(r"([a-z])([A-Z])", r"\1_\2", class_name)
        # Then, insert underscore before uppercase that follows uppercase and is followed by lowercase
        result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", result)
        return f"/{result.lower()}"


# Global registry instance
registry = TaskRegistry()
