"""Task routing endpoints"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from ..manager import task_manager
from ..task import ExampleCPUTask, ExampleIOTask

# Get the static directory path for serving files
static_path = Path(__file__).parent / "static"

router = APIRouter(
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


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


@router.post("/example_cpu_task")
async def example_task(name: str = "Example Task"):
    """Create and queue an example CPU task with the specified name"""

    # Create the example task
    task = ExampleCPUTask(name=name)

    # Add to queue
    task_id = await task_manager.add_task_to_queue(task)
    return {"task_id": task_id}


@router.post("/example_io_task")
async def progress_hook_example_task():
    """example task that does nothing"""

    # Create the example task
    task = ExampleIOTask()

    # Add to queue
    task_id = await task_manager.add_task_to_queue(task)
    return {"task_id": task_id}


@router.post("/example_recurring_cpu_task")
async def example_recurring_cpu_task(
    cron_expression: str = "*/1 * * * *", max_concurrent: int = 1
):
    """Create and register a recurring CPU task"""

    # Create the template task
    template_task = ExampleCPUTask(name="Recurring CPU Task")

    # Add as recurring task
    recurring_id = await task_manager.add_recurring_task(
        cron_expression=cron_expression,
        template_task=template_task,
        max_concurrent=max_concurrent,
    )

    return {
        "recurring_id": recurring_id,
        "message": f"Recurring task created with cron: {cron_expression}",
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
