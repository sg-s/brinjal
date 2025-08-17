# Getting Started with Brinjal

This guide will help you get up and running with Brinjal, a generic task management system for FastAPI applications.

## Installation

### From PyPI (Recommended)

```bash
pip install brinjal
```

### From Source

```bash
git clone https://github.com/sg-s/brinjal.git
cd brinjal
uv sync
```

## Quick Start

### 1. Basic Integration

The simplest way to use Brinjal is to include its router in your FastAPI application:

```python
from fastapi import FastAPI
from brinjal.api.router import router as brinjal_router

app = FastAPI()

# Include brinjal with your desired prefix
app.include_router(brinjal_router, prefix="/api/tasks")
```

That's it! Your app now has access to:

- `GET /api/tasks/queue` - List all tasks
- `POST /api/tasks/example_task` - Create an example task
- `GET /api/tasks/{task_id}/stream` - Stream task updates via SSE
- `GET /api/tasks/static/*` - Static files (TaskList.js, etc.)

### 2. Advanced Integration with Custom Endpoints

For more complex applications, you can extend Brinjal's functionality:

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

### 3. Frontend Integration

Brinjal includes a reusable web component for displaying tasks:

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <!-- Load the TaskList component from your brinjal endpoint -->
    <script src="/api/tasks/static/TaskList.js"></script>
    
    <!-- Use the component -->
    <task-list base_url="https://yourdomain.com"></task-list>
</body>
</html>
```

## Testing Your Integration

### 1. Start Your Application

```bash
uvicorn your_app:app --reload
```

### 2. Test the Endpoints

```bash
# Create an example task
curl -X POST "http://localhost:8000/api/tasks/example_task"

# Check the task queue
curl "http://localhost:8000/api/tasks/queue"

# Stream task updates (replace {task_id} with actual ID)
curl "http://localhost:8000/api/tasks/{task_id}/stream"
```

### 3. Test the Web Interface

Open your browser and navigate to:
- `http://localhost:8000/api/tasks/test` - Test page with TaskList component

## Creating Custom Tasks

Brinjal provides a base `Task` class that you can extend:

```python
from brinjal.task import Task
import time

class MyCustomTask(Task):
    def run(self):
        """Implement your synchronous work here"""
        for i in range(10):
            self.progress = i * 10
            time.sleep(1)
        
        self.status = "done"
        self.progress = 100
        self.heading = "Custom Task Complete"
        self.body = "This task did something amazing!"

# Use with the task manager
from brinjal.manager import task_manager

task = MyCustomTask()
task_id = await task_manager.add_task_to_queue(task)
```

## Configuration

### Task Manager Settings

The task manager can be configured when creating custom instances:

```python
from brinjal.manager import TaskManager

# Create a custom task manager
custom_manager = TaskManager()

# Start the worker loop
await custom_manager.start()

# Add tasks
task_id = await custom_manager.add_task_to_queue(task)
```

### Environment Variables

Brinjal respects standard FastAPI configuration. You can set:

- `LOG_LEVEL` - Logging level (default: INFO)
- `WORKER_CONCURRENCY` - Number of concurrent workers (default: 1)

## Troubleshooting

### Common Issues

1. **Static files not loading**: Ensure your router is properly included with the correct prefix
2. **Tasks not executing**: Check that the task manager is started (`await task_manager.start()`)
3. **SSE not working**: Verify the stream endpoint is accessible and the task exists

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

- Read the [API Reference](api-reference.md) for detailed endpoint documentation
- Check out [Task Development](task-development.md) for advanced task creation patterns
- Explore the [examples](../examples/) directory for more use cases

## Getting Help

- **Issues**: Report bugs on [GitHub](https://github.com/sg-s/brinjal/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/sg-s/brinjal/discussions)
- **Documentation**: Browse the full documentation at [docs.brinjal.dev](https://docs.brinjal.dev)
