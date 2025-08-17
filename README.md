# 🍆 Brinjal

![](docs/images/hero.gif)

A generic, reusable task management system built with FastAPI and asyncio. Brinjal provides a foundation for building applications that need to manage long-running tasks with real-time progress updates via Server-Sent Events (SSE).

## Features

- **Generic Task Framework**: Base `Task` class that can be extended for any type of work
- **Real-time Updates**: Server-Sent Events (SSE) for live progress monitoring
- **Asynchronous Execution**: Built on asyncio for non-blocking task processing
- **Web Component**: Reusable `<task-list>` component for displaying tasks
- **Self-contained**: No external static file mounting required
- **Easy Integration**: Simple router inclusion for any FastAPI application

## Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd brinjal

# Install dependencies
make install

# Run the development server
make dev
```

### Testing End-to-End

1. **Start the server:**
   ```bash
   make dev
   ```

2. **Create an example task:**
   ```bash
   curl -X POST "http://localhost:8000/api/tasks/example_task"
   ```

3. **Check task status:**
   ```bash
   curl "http://localhost:8000/api/tasks/queue"
   ```

4. **Stream real-time updates:**
   ```bash
   # Replace {task_id} with the actual task ID from step 2
   curl "http://localhost:8000/api/tasks/{task_id}/stream"
   ```

5. **View the web interface:**
   - Open `http://localhost:8000/api/tasks/test` in your browser
   - See the TaskList component in action

## Usage in Your Project

### Basic Integration

```python
from fastapi import FastAPI
from brinjal.api.router import router

app = FastAPI()
app.include_router(router)

# That's it! Your app now has:
# - /api/tasks/queue - List all tasks
# - /api/tasks/{task_id}/stream - SSE stream for task updates
# - /api/tasks/static/* - Static files (TaskList.js, etc.)
```

### Creating Custom Tasks

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
```

### Using the TaskList Component

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <task-list base_url="http://localhost:8000"></task-list>
    <script src="http://localhost:8000/api/tasks/static/TaskList.js"></script>
</body>
</html>
```

## API Reference

### Endpoints

- `POST /api/tasks/example_task` - Create an example task
- `GET /api/tasks/queue` - Get all tasks
- `GET /api/tasks/{task_id}/stream` - SSE stream for task updates
- `GET /api/tasks/static/{file}` - Static files (TaskList.js, etc.)

### Task Model

```python
@dataclass
class Task:
    task_id: str
    status: str  # "pending", "running", "done", "failed"
    progress: int  # 0-100
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
```

## Development

```bash
# Install dependencies
make install

# Run development server
make dev

# Run tests
make test

# Lint code
make lint

# Format code
make format

# Clean up
make clean
```

## Architecture

- **`Task`**: Base class for all tasks
- **`TaskManager`**: Manages task queue and execution
- **`TaskUpdate`**: Pydantic model for task updates
- **`ExampleTask`**: Sample implementation
- **`TaskList.js`**: Web component for displaying tasks

## License

[Your License Here]
