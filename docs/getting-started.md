# Getting Started with Brinjal

This guide will walk you through installing Brinjal and testing it end-to-end.

## Prerequisites

- Python 3.13 or higher
- `uv` package manager (recommended) or `pip`
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd brinjal
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
make install

# Or manually with uv
uv sync

# Or with pip
pip install -e .
```

### 3. Verify Installation

```bash
# Check if the package can be imported
python -c "import brinjal; print('Brinjal installed successfully!')"
```

## Running the Development Server

### Start the Server

```bash
make dev
```

This will start the FastAPI server on `http://localhost:8000` with auto-reload enabled.

### Verify the Server is Running

```bash
curl http://localhost:8000/docs
```

You should see the FastAPI interactive documentation.

## End-to-End Testing

### 1. Create an Example Task

```bash
curl -X POST "http://localhost:8000/api/tasks/example_task"
```

**Expected Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**What Happens:**
- A new `ExampleTask` is created and added to the task queue
- The task starts executing automatically
- Progress updates are sent every 0.1 seconds

### 2. Check Task Status

```bash
curl "http://localhost:8000/api/tasks/queue"
```

**Expected Response:**
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

### 3. Stream Real-Time Updates

```bash
# Replace {task_id} with the actual task ID from step 1
curl "http://localhost:8000/api/tasks/{task_id}/stream"
```

**Expected Output:**
```
data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 0, "img": null, "heading": null, "body": null}

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 10, "img": null, "heading": null, "body": null}

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "running", "progress": 20, "img": null, "heading": null, "body": null}

...

data: {"task_id": "550e8400-e29b-41d4-a716-446655440000", "task_type": "ExampleTask", "status": "done", "progress": 100, "img": null, "heading": null, "body": null}
```

**What You'll See:**
- Initial task state
- Progress updates every 0.1 seconds (0, 1, 2, ..., 99, 100)
- Final status when complete

### 4. Test the Web Interface

Open your browser and navigate to:
```
http://localhost:8000/api/tasks/test
```

**What You'll See:**
- A clean HTML page with Bootstrap styling
- The TaskList component displaying tasks
- Real-time updates as tasks progress
- Progress bars that move automatically

### 5. Create Multiple Tasks

```bash
# Create several tasks in parallel
curl -X POST "http://localhost:8000/api/tasks/example_task" &
curl -X POST "http://localhost:8000/api/tasks/example_task" &
curl -X POST "http://localhost:8000/api/tasks/example_task" &
wait
```

**What Happens:**
- Multiple tasks are created simultaneously
- Each task runs independently
- The web interface shows all tasks
- Progress bars update in real-time for each task

## Troubleshooting

### Common Issues

**Task not starting:**
```bash
# Check if the worker loop is running
curl "http://localhost:8000/api/tasks/queue"
```

**Static files not loading:**
```bash
# Verify the static file route works
curl "http://localhost:8000/api/tasks/static/TaskList.js"
```

**SSE not working:**
```bash
# Check if the task exists
curl "http://localhost:8000/api/tasks/queue"
# Then try streaming with the correct task ID
```

### Debug Mode

To see detailed logs, check the terminal where you ran `make dev`. You should see:
- Worker loop starting
- Tasks being picked up
- Progress updates being sent
- Task completion messages

## Next Steps

Now that you've tested Brinjal end-to-end:

1. [Learn how to create custom tasks](./task-development.md)
2. [Understand the API endpoints](./api-reference.md)
3. [Integrate Brinjal into your project](./integration.md)
4. [Explore the web component](./web-component.md)

## Summary

You've successfully:
- ✅ Installed Brinjal
- ✅ Started the development server
- ✅ Created and monitored tasks
- ✅ Viewed real-time progress updates
- ✅ Tested the web interface
- ✅ Verified SSE streaming works

Brinjal is ready to use! The system automatically handles task execution, progress monitoring, and real-time updates. You can now focus on implementing your specific task logic.
