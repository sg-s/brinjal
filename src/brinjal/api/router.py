"""Task routing endpoints"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from ..manager import task_manager

from ..task import ExampleTask

from pathlib import Path

# Get the static directory path for serving files
static_path = Path(__file__).parent / "static"

router = APIRouter(
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


@router.on_event("startup")
async def startup_event():
    await task_manager.start()


@router.on_event("shutdown")
async def shutdown_event():
    await task_manager.stop()


@router.get("/queue")
async def get_all_tasks():
    """Return all enqueued and running tasks with their status and progress."""
    return task_manager.get_all_tasks()


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


@router.post("/example_task")
async def example_task():
    """example task that does nothing"""

    # Create the example task
    task = ExampleTask()

    # Add to queue
    task_id = await task_manager.add_task_to_queue(task)
    return {"task_id": task_id}


@router.get("/test", response_class=HTMLResponse)
async def test():
    """test endpoint that returns the test.html file"""
    test_html_path = static_path / "test.html"
    try:
        with open(test_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="test.html not found")


@router.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    """Serve static files from the brinjal package"""
    file_path_obj = static_path / file_path

    # Security check: ensure the file is within the static directory
    try:
        file_path_obj.resolve().relative_to(static_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path_obj)
