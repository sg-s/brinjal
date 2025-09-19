# API Reference

## Overview

The Brinjal API provides endpoints for managing tasks, monitoring progress, and streaming real-time updates. The system uses semaphore-based concurrency control to efficiently manage both CPU-bound and I/O-bound tasks.

## Task Concurrency System

### Semaphore Types

Tasks can specify their concurrency behavior using the `semaphore_name` field:

- **`"single"`**: Only one task can run at a time (CPU-bound tasks)
- **`"multiple"`**: Up to 10 tasks can run concurrently (I/O-bound tasks)
- **`"default"`**: Fallback with limit of 3 concurrent tasks

### Task Status Flow

1. **`queued`** - Task is in the queue, waiting to be picked up
2. **`running`** - Task has acquired its semaphore and is executing
3. **`done`** - Task completed successfully
4. **`failed`** - Task encountered an error

## Endpoints

### Queue Management

#### GET `/queue`

Returns all enqueued and running tasks with their status and progress.

**Response:**
```json
[
  {
    "task_id": "uuid-string",
    "parent_id": "uuid-string",
    "task_type": "ExampleTask",
    "status": "running",
    "progress": 75,
    "img": "icon.png",
    "heading": "Task Title",
    "body": "Task description",
    "started_at": "2024-01-01T12:00:00",
    "completed_at": null
  }
]
```

#### GET `/queue/stream`

Streams real-time updates when tasks are added/removed from the queue using Server-Sent Events.

**Events:**
- `task_added`: New task added to queue
- `task_removed`: Task removed from queue
- `queue_updated`: Complete queue state update

### Individual Task Management

#### GET `/{task_id}/stream`

Streams real-time updates for a specific task using Server-Sent Events.

**Events:**
- Task status changes
- Progress updates
- Completion notifications

#### DELETE `/{task_id}`

Deletes a task by ID from the store.

**Response:**
```json
{
  "message": "Task {task_id} deleted successfully"
}
```

### Task Creation

#### POST `/example_cpu_task`

Creates and queues an example CPU-bound task (uses "single" semaphore).

**Response:**
```json
{
  "task_id": "uuid-string"
}
```

#### POST `/example_io_task`

Creates and queues an example I/O-bound task (uses "multiple" semaphore).

**Response:**
```json
{
  "task_id": "uuid-string"
}
```

### Recurring Tasks

#### GET `/recurring`

Returns all registered recurring tasks with their configuration and status.

**Response:**
```json
[
  {
    "recurring_id": "uuid-string",
    "cron_expression": "*/5 * * * *",
    "task_type": "ExampleCPUTask",
    "max_concurrent": 2,
    "enabled": true,
    "next_run": "2024-01-01T12:05:00",
    "last_run": "2024-01-01T12:00:00",
    "consecutive_failures": 0,
    "total_runs": 5,
    "total_failures": 0,
    "created_at": "2024-01-01T10:00:00"
  }
]
```

**Response Fields:**
- `recurring_id`: Unique identifier for the recurring task
- `cron_expression`: Cron expression defining when the task should run
- `task_type`: Type of task that gets created (class name)
- `max_concurrent`: Maximum number of instances that can run simultaneously
- `enabled`: Whether the recurring task is currently enabled
- `next_run`: ISO timestamp of when the task will run next (null if disabled)
- `last_run`: ISO timestamp of when the task last ran (null if never run)
- `consecutive_failures`: Number of consecutive failures
- `total_runs`: Total number of times the task has been executed
- `total_failures`: Total number of times the task has failed
- `created_at`: ISO timestamp when the recurring task was created

#### PATCH `/recurring/{recurring_id}/enable`

Enable a recurring task by ID.

**Parameters:**
- `recurring_id` (path): The unique identifier of the recurring task

**Response:**
```json
{
  "message": "Recurring task {recurring_id} enabled successfully"
}
```

**Error Responses:**
- `404`: Recurring task not found

#### PATCH `/recurring/{recurring_id}/disable`

Disable a recurring task by ID.

**Parameters:**
- `recurring_id` (path): The unique identifier of the recurring task

**Response:**
```json
{
  "message": "Recurring task {recurring_id} disabled successfully"
}
```

**Error Responses:**
- `404`: Recurring task not found

## Task Models

### Task Base Class

```python
@dataclass
class Task:
    task_id: str
    parent_id: Optional[str]
    status: str  # "queued", "running", "done", "failed"
    progress: int  # 0-100
    results: Optional[Any]
    semaphore_name: str  # "single", "multiple", "default"
    img: Optional[str]
    heading: Optional[str]
    body: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

### TaskUpdate Model

```python
class TaskUpdate(BaseModel):
    task_id: str
    parent_id: Optional[str]
    task_type: str
    status: str
    progress: int
    img: Optional[str]
    heading: Optional[str]
    body: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
```

## Concurrency Behavior

### Single Semaphore Tasks

- **Limit**: 1 concurrent execution
- **Use Case**: CPU-bound tasks, heavy computation
- **Behavior**: Tasks queue up and execute one at a time
- **Example**: `ExampleCPUTask` (simulates CPU work)

### Multiple Semaphore Tasks

- **Limit**: 10 concurrent executions
- **Use Case**: I/O-bound tasks, network requests, file operations
- **Behavior**: Multiple tasks can run simultaneously
- **Example**: `ExampleIOTask` (simulates I/O work)

### Default Semaphore Tasks

- **Limit**: 3 concurrent executions
- **Use Case**: Unknown workload types, fallback option
- **Behavior**: Moderate concurrency for mixed workloads

## Real-Time Updates

### Server-Sent Events (SSE)

All streaming endpoints use SSE for real-time updates:

```
data: {"type": "task_added", "task": {...}}

data: {"type": "progress_update", "task_id": "...", "progress": 50}

data: {"type": "task_completed", "task_id": "...", "status": "done"}
```

### Event Types

- **Task Lifecycle**: `task_added`, `task_started`, `task_completed`, `task_failed`
- **Progress Updates**: `progress_update`
- **Queue Changes**: `queue_updated`

## Error Handling

### HTTP Status Codes

- **200**: Success
- **404**: Task not found
- **500**: Internal server error

### Error Response Format

```json
{
  "detail": "Error description"
}
```

## Performance Considerations

### Concurrency Limits

- **Single tasks**: May queue up under high load
- **Multiple tasks**: Can overwhelm external systems
- **Default tasks**: Balanced approach for mixed workloads

### Monitoring

- Check `/queue` endpoint for current task status
- Use SSE streams for real-time monitoring
- Monitor semaphore acquisition in logs

## Examples

### Creating a CPU-Bound Task

```python
import requests

# Create CPU-intensive task
response = requests.post("http://localhost:8000/api/tasks/example_cpu_task")
task_id = response.json()["task_id"]

# Monitor progress
import sseclient
client = sseclient.SSEClient(f"http://localhost:8000/api/tasks/{task_id}/stream")
for event in client.events():
    data = json.loads(event.data)
    print(f"Progress: {data['progress']}%")
    if data['status'] in ['done', 'failed']:
        break
```

### Creating an I/O-Bound Task

```python
# Create I/O-intensive task
response = requests.post("http://localhost:8000/api/tasks/example_io_task")
task_id = response.json()["task_id"]

# Monitor queue for all tasks
client = sseclient.SSEClient("http://localhost:8000/api/tasks/queue/stream")
for event in client.events():
    data = json.loads(event.data)
    if data['type'] == 'queue_updated':
        print(f"Queue has {len(data['tasks'])} tasks")
```

## Best Practices

1. **Choose appropriate semaphores** based on task characteristics
2. **Monitor task progress** using SSE streams
3. **Handle errors gracefully** in your client code
4. **Clean up resources** when tasks complete
5. **Use appropriate timeouts** for long-running operations

## Search Tasks

Search for tasks by attribute/value pairs using exact matching.

**Endpoint:** `POST /search`

**Request Body:** JSON object where keys are attribute names and values are expected values. All criteria must match (AND logic).

**Response:** JSON object containing an array of matching task IDs.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Task",
    "status": "running"
  }'
```

**Example Response:**
```json
{
  "task_ids": ["task-id-1", "task-id-2"]
}
```

**Search Criteria Examples:**

- Search by task name: `{"name": "Task A"}`
- Search by status: `{"status": "done"}`
- Search by task type: `{"task_type": "ExampleCPUTask"}`
- Search by semaphore: `{"semaphore_name": "single"}`
- Search by multiple criteria: `{"name": "Task A", "status": "running", "semaphore_name": "single"}`

**Notes:**
- All search criteria use exact matching
- Multiple criteria are combined with AND logic
- The `task_type` attribute is a special case that matches against the class name
- Returns an empty list if no tasks match or if attributes don't exist
- Works with any Task subclass attributes, making it flexible for future task types
