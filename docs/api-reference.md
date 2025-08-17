# API Reference

This document provides a comprehensive reference for all Brinjal API endpoints, data models, and integration patterns.

## Overview

Brinjal provides a generic task management system that can be integrated into any FastAPI application. The API is designed to be flexible and prefix-free, allowing you to control the URL structure in your application.

## Integration Patterns

### Basic Integration

```python
from fastapi import FastAPI
from brinjal.api.router import router as brinjal_router

app = FastAPI()

# Include brinjal with your desired prefix
app.include_router(brinjal_router, prefix="/api/tasks")
```

### Advanced Integration with Custom Endpoints

```python
from fastapi import APIRouter
from brinjal.api.router import router as brinjal_router
from brinjal.manager import task_manager

# Create your main router with the desired prefix
router = APIRouter(prefix="/api/tasks")

# Include all of brinjal's functionality
router.include_router(brinjal_router)

# Add your custom endpoints
@router.post("/custom_task")
async def custom_task():
    # Your custom logic here
    pass

# Include in your main app
app.include_router(router)
```

## Endpoints

### Task Management

#### `GET /api/tasks/queue`

Returns all tasks in the system with their current status and progress.

**Response:**
```json
[
  {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "ExampleTask",
    "status": "running",
    "progress": 45,
    "img": null,
    "heading": null,
    "body": null
  }
]
```

#### `POST /api/tasks/example_task`

Creates and starts a new example task.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Real-time Updates

#### `GET /api/tasks/{task_id}/stream`

Streams real-time updates for a specific task using Server-Sent Events (SSE).

**Parameters:**
- `task_id` (string): The unique identifier of the task

**Response:** Server-Sent Events stream
```
data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 0, "img": null, "heading": null, "body": null}

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 10, "img": null, "heading": null, "body": null}

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "done", "progress": 100, "img": null, "heading": null, "body": null}
```

### Static Files

#### `GET /api/tasks/static/{file_path}`

Serves static files from the brinjal package, including the TaskList web component.

**Parameters:**
- `file_path` (string): Path to the static file within the brinjal package

**Available Files:**
- `TaskList.js` - The TaskList web component
- `test.html` - Test page for the TaskList component

**Example:**
```bash
curl "http://localhost:8000/api/tasks/static/TaskList.js"
```

### Testing

#### `GET /api/tasks/test`

Returns a test HTML page that demonstrates the TaskList component in action.

**Response:** HTML page with embedded TaskList component

## Data Models

### TaskUpdate

Generic model for task updates sent via SSE.

```python
class TaskUpdate(BaseModel):
    task_id: str
    task_type: str
    status: Literal["pending", "running", "done", "failed", "cancelled"] = "pending"
    progress: int
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
```

**Fields:**
- `task_id`: Unique identifier for the task
- `task_type`: Class name of the task (e.g., "ExampleTask")
- `status`: Current status of the task
- `progress`: Progress percentage (0-100)
- `img`: Optional image URL for the task
- `heading`: Optional title/heading for the task
- `body`: Optional description text for the task

## Task Manager

### Global Instance

Brinjal provides a global task manager instance that you can use directly:

```python
from brinjal.manager import task_manager

# Start the worker loop
await task_manager.start()

# Add a task
task = ExampleTask()
task_id = await task_manager.add_task_to_queue(task)

# Get task information
task = task_manager.get_task(task_id)
all_tasks = task_manager.get_all_tasks()

# Stop the worker loop
await task_manager.stop()
```

### Custom Instance

You can also create custom task manager instances:

```python
from brinjal.manager import TaskManager

# Create a custom instance
custom_manager = TaskManager()

# Start the worker loop
await custom_manager.start()

# Use the custom instance
task_id = await custom_manager.add_task_to_queue(task)
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `404 Not Found`: Task or file not found
- `403 Forbidden`: Access denied (for static file security)
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Task not found"
}
```

## Security Considerations

### Static File Access

The static file endpoint includes security checks to prevent directory traversal attacks:

- Files must be within the brinjal package's static directory
- Relative paths are resolved and validated
- Access outside the static directory is denied

### Task Isolation

- Each task runs in its own context
- Tasks cannot access other tasks' data
- Progress updates are isolated per task

## Performance

### Task Execution

- Tasks run asynchronously using asyncio
- Long-running operations use `asyncio.to_thread` to avoid blocking
- Progress updates are batched to prevent overwhelming the client

### SSE Optimization

- Server-Sent Events are streamed efficiently
- Connection state is monitored for disconnections
- Unused connections are cleaned up automatically

## Monitoring and Debugging

### Logging

Brinjal uses Python's standard logging module:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Monitor the task manager status:

```python
from brinjal.manager import task_manager

# Check if worker loop is running
is_running = task_manager._worker_task is not None and not task_manager._worker_task.done()

# Get queue size
queue_size = task_manager.task_queue.qsize()
```

## Examples

### Complete Integration Example

```python
from fastapi import FastAPI
from brinjal.api.router import router as brinjal_router
from brinjal.manager import task_manager

app = FastAPI(title="My Task App")

# Include brinjal
app.include_router(brinjal_router, prefix="/api/tasks")

@app.on_event("startup")
async def startup():
    await task_manager.start()

@app.on_event("shutdown")
async def shutdown():
    await task_manager.stop()

# Your custom endpoints here
@app.post("/api/tasks/custom")
async def custom_endpoint():
    # Your logic here
    pass
```

### Frontend Integration Example

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1>My Task Dashboard</h1>
        
        <!-- Load the TaskList component -->
        <script src="/api/tasks/static/TaskList.js"></script>
        
        <!-- Use the component -->
        <task-list base_url="https://myapp.com"></task-list>
    </div>
</body>
</html>
```

## Troubleshooting

### Common Issues

1. **Tasks not executing**: Ensure `task_manager.start()` is called
2. **SSE not working**: Check that the task exists and the stream endpoint is accessible
3. **Static files 404**: Verify the router is included with the correct prefix
4. **Import errors**: Ensure brinjal is properly installed

### Debug Steps

1. Check application logs for errors
2. Verify endpoint accessibility with curl
3. Test SSE streaming manually
4. Check browser console for JavaScript errors

## Support

For additional help:

- **Documentation**: [docs.brinjal.dev](https://docs.brinjal.dev)
- **Issues**: [GitHub Issues](https://github.com/sg-s/brinjal/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sg-s/brinjal/discussions)
