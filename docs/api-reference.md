# API Reference

This document provides a complete reference for all Brinjal API endpoints, data models, and response formats.

## Base URL

All API endpoints are prefixed with `/api/tasks`.

## Authentication

Currently, Brinjal does not implement authentication. All endpoints are publicly accessible.

## Endpoints

### Task Management

#### Create Example Task

```http
POST /api/tasks/example_task
```

Creates a new example task and adds it to the execution queue.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/tasks/example_task"
```

#### Get All Tasks

```http
GET /api/tasks/queue
```

Returns a list of all tasks with their current status and progress.

**Response:**
```json
[
  {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_type": "ExampleTask",
    "status": "running",
    "progress": 45,
    "results": null,
    "video_id": null,
    "channel_id": null
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/api/tasks/queue"
```

#### Stream Task Updates

```http
GET /api/tasks/{task_id}/stream
```

Streams real-time updates for a specific task using Server-Sent Events (SSE).

**Parameters:**
- `task_id` (string): The unique identifier of the task

**Response:**
```
data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 0, "img": null, "heading": null, "body": null}

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 10, "img": null, "heading": null, "body": null}

...

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "done", "progress": 100, "img": null, "heading": null, "body": null}
```

**Example:**
```bash
curl "http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000/stream"
```

**Notes:**
- This endpoint returns a Server-Sent Events stream
- Each line starting with `data:` contains a JSON object
- The stream continues until the task is complete or the client disconnects
- Keepalive messages (`: keepalive`) are sent every 10 seconds

### Static Files

#### Get Static File

```http
GET /api/tasks/static/{file_path}
```

Serves static files from the Brinjal package.

**Parameters:**
- `file_path` (string): Path to the file within the static directory

**Available Files:**
- `TaskList.js` - The TaskList web component
- `test.html` - Test page for the TaskList component

**Example:**
```bash
curl "http://localhost:8000/api/tasks/static/TaskList.js"
```

### Testing

#### Get Test Page

```http
GET /api/tasks/test
```

Returns an HTML page that demonstrates the TaskList component.

**Response:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brinjal TaskList Test</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <h1>Brinjal TaskList Test</h1>
        <task-list base_url="http://localhost:8000"></task-list>
    </div>
    <script src="/api/tasks/static/TaskList.js"></script>
</body>
</html>
```

**Example:**
```bash
curl "http://localhost:8000/api/tasks/test"
```

## Data Models

### Task

The base task model that all tasks inherit from.

```python
@dataclass
class Task:
    task_id: str                    # Unique identifier
    status: str                     # Current status
    progress: int                   # Progress percentage (0-100)
    results: Optional[Any]          # Task results
    update_queue: asyncio.Queue     # Internal update queue
    loop: Optional[asyncio.AbstractEventLoop]  # Event loop reference
    img: Optional[str]              # Image URL for display
    heading: Optional[str]          # Task title
    body: Optional[str]             # Task description
```

**Status Values:**
- `"pending"` - Task is queued but not yet started
- `"running"` - Task is currently executing
- `"done"` - Task completed successfully
- `"failed"` - Task failed with an error
- `"cancelled"` - Task was cancelled

### TaskUpdate

Pydantic model for task updates sent via SSE.

```python
class TaskUpdate(BaseModel):
    task_id: str
    task_type: str
    status: Literal["pending", "running", "done", "failed", "cancelled"]
    progress: int
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
```

### ExampleTask

A sample task implementation for testing and demonstration.

```python
@dataclass
class ExampleTask(Task):
    def run(self):
        """Synchronous function that does the actual work"""
        import time
        
        for i in range(100):
            self.progress = i
            time.sleep(0.1)
        
        self.progress = 100
        self.status = "done"
```

## Error Responses

### 404 Not Found

```json
{
  "detail": "Task not found"
}
```

Returned when:
- Requesting a task that doesn't exist
- Accessing a static file that doesn't exist

### 403 Forbidden

```json
{
  "detail": "Access denied"
}
```

Returned when:
- Attempting to access files outside the static directory (security measure)

## Rate Limiting

Currently, Brinjal does not implement rate limiting. All endpoints can be called as frequently as needed.

## CORS

Brinjal does not implement CORS headers. If you need CORS support, you'll need to add it to your FastAPI application.

## WebSocket Support

Brinjal uses Server-Sent Events (SSE) instead of WebSockets for real-time updates. SSE is simpler to implement and provides one-way communication from server to client, which is perfect for task progress updates.

## Examples

### Complete Task Lifecycle

1. **Create a task:**
   ```bash
   curl -X POST "http://localhost:8000/api/tasks/example_task"
   # Response: {"task_id": "abc123"}
   ```

2. **Check initial status:**
   ```bash
   curl "http://localhost:8000/api/tasks/queue"
   # Response: [{"task_id": "abc123", "status": "pending", ...}]
   ```

3. **Stream updates:**
   ```bash
   curl "http://localhost:8000/api/tasks/abc123/stream"
   # Streams progress updates until completion
   ```

4. **Check final status:**
   ```bash
   curl "http://localhost:8000/api/tasks/queue"
   # Response: [{"task_id": "abc123", "status": "done", ...}]
   ```

### Using with JavaScript

```javascript
// Create a task
const response = await fetch('/api/tasks/example_task', {
    method: 'POST'
});
const { task_id } = await response.json();

// Stream updates
const eventSource = new EventSource(`/api/tasks/${task_id}/stream`);
eventSource.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log(`Task ${update.task_id}: ${update.progress}%`);
    
    if (update.status === 'done' || update.status === 'failed') {
        eventSource.close();
    }
};
```

## Next Steps

- [Learn how to create custom tasks](./task-development.md)
- [Explore integration options](./integration.md)
- [Understand the web component](./web-component.md)
- [See practical examples](./examples.md)
