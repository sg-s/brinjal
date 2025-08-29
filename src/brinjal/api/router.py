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


@router.on_event("startup")
async def startup_event():
    """Start the task manager on startup"""
    await task_manager.start()


@router.on_event("shutdown")
async def shutdown_event():
    """Stop the task manager on shutdown"""
    await task_manager.stop()


@router.get("/queue")
async def get_all_tasks():
    """Return all enqueued and running tasks with their status and progress."""
    return task_manager.get_all_tasks()


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
        raise HTTPException(status_code=404, detail="Task not found")

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
            raise HTTPException(status_code=404, detail="Task not found")

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
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error deleting task {task_id}: {e}", exc_info=True)
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
