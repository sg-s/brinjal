"""Task routing endpoints"""

import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union, get_args, get_origin

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Query,
    Request,
    Request as FastAPIRequest,
)
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, create_model

from ..manager import task_manager
from ..registry import registry, TaskRegistry
from ..task import ExampleCPUTask, ExampleIOTask, Task

# Get the static directory path for serving files
static_path = Path(__file__).parent / "static"

router = APIRouter(
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


def _create_request_model(
    task_class: Type[Task], params: list
) -> Optional[Type[BaseModel]]:
    """Create a Pydantic model for request validation from task parameters."""
    if not params:
        return None

    field_definitions = {}

    for param in params:
        field_name = param["name"]
        field_type = param["type"]
        default_value = param["default"]
        required = param["required"]

        # Handle Optional types and Union types
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            # Check if it's Optional (Union[X, None] or Union[X, NoneType])
            if len(args) == 2 and type(None) in args:
                # Extract the non-None type
                actual_type = next(arg for arg in args if arg is not type(None))
                field_definitions[field_name] = (actual_type, None)
            else:
                # It's a Union but not Optional - use as is
                field_definitions[field_name] = (
                    field_type,
                    default_value if not required else ...,
                )
        elif required:
            field_definitions[field_name] = (field_type, ...)
        else:
            field_definitions[field_name] = (field_type, default_value)

    model_name = f"{task_class.__name__}Request"
    return create_model(model_name, **field_definitions)


def _generate_task_route(task_class: Type[Task], route_path: str):
    """Generate a FastAPI route handler for a Task class."""
    params = registry.get_route_params(task_class)

    # Create the route handler function
    if not params:
        # No parameters - create a simple handler
        async def route_handler():
            """Auto-generated route for {task_class.__name__}"""
            task = task_class()
            task_id = await task_manager.add_task_to_queue(task)
            return {"task_id": task_id}
    else:
        # Use Request to accept both query params and JSON body
        async def route_handler(request: FastAPIRequest):
            """Auto-generated route for {task_class.__name__}"""
            task_kwargs = {}

            # Try to get JSON body first
            try:
                body_data = await request.json()
                if body_data:
                    task_kwargs.update(body_data)
            except Exception:
                pass  # No JSON body, will use query params

            # Extract from query parameters (overrides body if both present)
            for param in params:
                field_name = param["name"]
                default_value = param["default"]

                # Check query params
                if field_name in request.query_params:
                    query_value = request.query_params[field_name]
                    # Try to parse based on type
                    field_type = param["type"]
                    origin = get_origin(field_type)
                    if origin is Union:
                        args = get_args(field_type)
                        if len(args) == 2 and type(None) in args:
                            actual_type = next(
                                arg for arg in args if arg is not type(None)
                            )
                        else:
                            actual_type = field_type
                    else:
                        actual_type = field_type

                    # Parse the value
                    if actual_type == bool:
                        task_kwargs[field_name] = query_value.lower() in (
                            "true",
                            "1",
                            "yes",
                        )
                    elif actual_type == int:
                        task_kwargs[field_name] = int(query_value)
                    elif actual_type == float:
                        task_kwargs[field_name] = float(query_value)
                    else:
                        task_kwargs[field_name] = query_value
                elif field_name not in task_kwargs and default_value is not None:
                    # Use default if not provided
                    task_kwargs[field_name] = default_value

            # Create task instance
            task = task_class(**task_kwargs)

            # Add to queue
            task_id = await task_manager.add_task_to_queue(task)
            return {"task_id": task_id}

    # Update function metadata
    route_handler.__name__ = f"create_{task_class.__name__.lower()}"
    route_handler.__doc__ = f"Create and queue a {task_class.__name__} task"

    return route_handler, None


def register_task_routes():
    """Register all Task subclasses and generate routes for them."""
    # Register existing task classes
    registry.register(ExampleCPUTask)
    registry.register(ExampleIOTask)

    # Generate routes for all registered tasks
    for task_name, task_class in registry.get_all_tasks().items():
        route_path = TaskRegistry.class_name_to_route(task_name)

        # Skip if route already exists (for backward compatibility)
        # We'll remove manual routes later
        route_handler, request_model = _generate_task_route(task_class, route_path)

        # Register the route
        router.post(route_path, response_model=Dict[str, str])(route_handler)


# Register all task routes on module import
register_task_routes()


@router.get("/queue")
async def get_all_tasks():
    """Return all enqueued and running tasks with their status and progress."""
    return task_manager.get_all_tasks()


@router.get("/recurring")
async def get_recurring_tasks():
    """Return all registered recurring tasks with their configuration and status."""
    recurring_tasks = task_manager.get_all_recurring_tasks()

    # Convert RecurringTaskInfo objects to dictionaries for JSON serialization
    result = []
    for recurring_info in recurring_tasks:
        task_info = {
            "recurring_id": recurring_info.recurring_id,
            "cron_expression": recurring_info.cron_expression,
            "task_type": recurring_info.template_task.__class__.__name__,
            "max_concurrent": recurring_info.max_concurrent,
            "enabled": recurring_info.enabled,
            "next_run": recurring_info.next_run.isoformat()
            if recurring_info.next_run
            else None,
            "last_run": recurring_info.last_run.isoformat()
            if recurring_info.last_run
            else None,
            "consecutive_failures": recurring_info.consecutive_failures,
            "total_runs": recurring_info.total_runs,
            "total_failures": recurring_info.total_failures,
            "created_at": recurring_info.created_at.isoformat(),
        }
        result.append(task_info)

    return result


@router.patch("/recurring/{recurring_id}/enable")
async def enable_recurring_task(recurring_id: str):
    """Enable a recurring task by ID."""
    success = task_manager.enable_recurring_task(recurring_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Recurring task {recurring_id} not found"
        )

    return {"message": f"Recurring task {recurring_id} enabled successfully"}


@router.patch("/recurring/{recurring_id}/disable")
async def disable_recurring_task(recurring_id: str):
    """Disable a recurring task by ID."""
    success = task_manager.disable_recurring_task(recurring_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Recurring task {recurring_id} not found"
        )

    return {"message": f"Recurring task {recurring_id} disabled successfully"}


@router.post("/search")
async def search_tasks(search_criteria: dict):
    """Search for tasks by attribute/value pairs using exact matching.

    Accepts a JSON dict where keys are attribute names and values are expected values.
    All criteria must match (AND logic).
    Returns a list of task IDs that match all specified criteria.

    Examples:
        - {"name": "My Task", "status": "running"}
        - {"task_type": "ExampleCPUTask", "semaphore_name": "single"}
        - {"status": "done"}
    """
    # Perform the search using the provided criteria
    matching_task_ids = task_manager.search_tasks_by_attributes(search_criteria)

    return {"task_ids": matching_task_ids}


@router.get("/queue/stream")
async def stream_queue_updates(request: Request):
    """Stream real-time updates when tasks are added/removed from the queue"""
    # Get the event generator from the task manager for queue updates
    event_generator = task_manager.get_queue_sse_event_generator(request)
    if not event_generator:
        raise HTTPException(status_code=404, detail="Queue stream not available")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{task_id}/stream")
async def stream_task_updates(task_id: str, request: Request):
    """Stream real-time updates for a specific task"""
    # Check if task exists
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task with ID {task_id} not found")

    # Get the event generator from the task manager
    event_generator = task_manager.get_sse_event_generator(task_id, request)
    if not event_generator:
        raise HTTPException(status_code=404, detail="Task not found")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/completed")
async def delete_all_completed_tasks():
    """Delete all completed tasks (done or failed) from the store"""
    try:
        # Get all tasks and filter for completed ones
        all_tasks = task_manager.get_all_tasks()
        completed_tasks = [
            task for task in all_tasks if task.get("status") in ["done", "failed"]
        ]

        if not completed_tasks:
            return {
                "message": "No completed tasks found",
                "deleted_count": 0,
                "failed_count": 0,
            }

        # Delete all completed tasks
        deleted_count = 0
        failed_count = 0
        failed_task_ids = []

        for task in completed_tasks:
            task_id = task.get("task_id")
            if task_id:
                try:
                    removed_task = await task_manager.remove_task_from_store(task_id)
                    if removed_task:
                        deleted_count += 1
                    else:
                        failed_count += 1
                        failed_task_ids.append(task_id)
                except Exception:
                    failed_count += 1
                    failed_task_ids.append(task_id)

        return {
            "message": f"Deleted {deleted_count} completed task(s)",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_task_ids": failed_task_ids,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from None


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task by ID from the store"""
    try:
        # Check if task exists
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=404, detail="Task with ID {task_id} not found"
            )

        # Remove the task from the store
        removed_task = await task_manager.remove_task_from_store(task_id)
        if removed_task:
            return {"message": f"Task {task_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete task")
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors and return a generic error
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from None


@router.post("/recurring/{task_type}")
async def create_recurring_task(
    task_type: str,
    request: FastAPIRequest,
    cron_expression: str = Query(..., description="Cron expression for scheduling"),
    max_concurrent: int = Query(1, description="Maximum concurrent instances"),
):
    """Create a recurring task for any registered task type.

    Args:
        task_type: The registered task class name (e.g., "ExampleCPUTask")
        cron_expression: Cron expression defining when the task should run
        max_concurrent: Maximum number of instances that can run simultaneously
        request: FastAPI request object containing task parameters in JSON body or query params

    Returns:
        Dictionary with recurring_id and message
    """
    # Get the task class from registry
    try:
        task_class = registry.get_task_class(task_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    # Get task parameters
    params = registry.get_route_params(task_class)
    task_kwargs = {}

    # Try to get JSON body first
    try:
        body_data = await request.json()
        if body_data:
            task_kwargs.update(body_data)
    except Exception:
        # No JSON body, will use query params
        pass

        # Extract from query parameters (overrides body if both present)
        for param in params:
            field_name = param["name"]
            default_value = param["default"]

            # Skip cron_expression and max_concurrent as they're route params
            if field_name in ("cron_expression", "max_concurrent"):
                continue

        # Check query params
        if field_name in request.query_params:
            query_value = request.query_params[field_name]
            # Try to parse based on type
            field_type = param["type"]
            origin = get_origin(field_type)
            if origin is Union:
                args = get_args(field_type)
                if len(args) == 2 and type(None) in args:
                    actual_type = next(arg for arg in args if arg is not type(None))
                else:
                    actual_type = field_type
            else:
                actual_type = field_type

            # Parse the value
            if actual_type == bool:
                task_kwargs[field_name] = query_value.lower() in (
                    "true",
                    "1",
                    "yes",
                )
            elif actual_type == int:
                task_kwargs[field_name] = int(query_value)
            elif actual_type == float:
                task_kwargs[field_name] = float(query_value)
            else:
                task_kwargs[field_name] = query_value
        elif field_name not in task_kwargs and default_value is not None:
            # Use default if not provided
            task_kwargs[field_name] = default_value

    # Create template task instance
    template_task = task_class(**task_kwargs)

    # Add as recurring task
    recurring_id = await task_manager.add_recurring_task(
        cron_expression=cron_expression,
        template_task=template_task,
        max_concurrent=max_concurrent,
    )

    return {
        "recurring_id": recurring_id,
        "message": f"Recurring {task_type} task created with cron: {cron_expression}",
    }


@router.get("/test", response_class=HTMLResponse)
async def test():
    """test endpoint that returns the test.html file"""
    try:
        return FileResponse(static_path / "test.html", media_type="text/html")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="test.html not found") from None


@router.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    """Serve static files from the brinjal package"""
    file_path_obj = static_path / file_path

    # Security check: ensure the file is within the static directory
    try:
        file_path_obj.resolve().relative_to(static_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied") from None

    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path_obj)
