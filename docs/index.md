# 🍆 Brinjal: tasks made simple

Welcome to the Brinjal documentation! Brinjal is a generic, reusable task management system built with FastAPI and asyncio.

## What is Brinjal?

Brinjal provides a flexible foundation for building task-based applications with real-time progress updates via Server-Sent Events (SSE). It's designed to be easily integrated into any FastAPI application without hardcoded prefixes or assumptions about your URL structure.

## Key Features

- **Generic Task Framework**: Base `Task` class that can be extended for any type of work
- **Real-time Updates**: Server-Sent Events (SSE) for live progress monitoring
- **Asynchronous Execution**: Built on asyncio for non-blocking task processing
- **Flexible Integration**: No hardcoded prefixes - easily integrated into any FastAPI application
- **Web Components**: Reusable `<task-list>` component for displaying tasks
- **Self-contained**: No external static file mounting required
- **Automatic Task Pruning**: Keeps only the 10 most recent succeeded tasks to prevent memory bloat
- **Recurring Tasks**: Schedule tasks to run automatically using cron-like expressions

## Quick Start

### Installation

```bash
pip install brinjal
```

### Basic Integration

```python
from fastapi import FastAPI
from brinjal.api.router import router as brinjal_router

app = FastAPI()

# Include brinjal with your desired prefix
app.include_router(brinjal_router, prefix="/api/tasks")
```

That's it! Your app now has access to:
- Task management endpoints
- Real-time progress streaming
- Web components for the frontend

## Documentation Sections

### 🚀 [Getting Started](getting-started.md)
Learn how to install Brinjal and integrate it into your FastAPI application. Includes step-by-step examples and troubleshooting tips.

### 📚 [API Reference](api-reference.md)
Complete reference for all API endpoints, data models, and integration patterns. Essential for developers building with Brinjal.

### 🔧 [Task Development](task-development.md)
Learn how to create custom tasks by extending the base `Task` class. Includes examples and best practices.

### ⏰ [Recurring Tasks](recurring-tasks.md)
Learn how to set up automated recurring tasks using cron-like syntax. Includes scheduling, monitoring, and best practices.

### 🧹 [Task Management](task-management.md)
Learn about automatic task pruning, memory management, and how Brinjal keeps your system running efficiently.

## Architecture Overview

Brinjal is designed with separation of concerns in mind:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Brinjal       │    │   Your Custom   │
│                 │    │   Router        │    │   Endpoints     │
│                 │◄───┤                 │◄───┤                 │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Prefix   │    │   Generic       │    │   Application   │
│   /api/tasks    │    │   Functionality │    │   Logic         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Integration Patterns

### Simple Integration
```python
app.include_router(brinjal_router, prefix="/api/tasks")
```

### Advanced Integration with Custom Endpoints
```python
router = APIRouter(prefix="/api/tasks")
router.include_router(brinjal_router)

@router.post("/custom_task")
async def custom_task():
    # Your custom logic here
    pass

app.include_router(router)
```

## Examples

### Frontend Integration
```html
<!-- Load the TaskList component -->
<script src="/api/tasks/static/TaskList.js"></script>

<!-- Use the component -->
<task-list base_url="https://yourdomain.com"></task-list>
```

### Custom Task Creation
```python
from brinjal.task import Task

class MyCustomTask(Task):
    def run(self):
        # Your synchronous work here
        for i in range(10):
            self.progress = i * 10
            time.sleep(1)
        
        self.status = "done"
        self.progress = 100
```

## Getting Help

- **Issues**: Report bugs on [GitHub](https://github.com/sg-s/brinjal/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/sg-s/brinjal/discussions)
- **Documentation**: Browse the full documentation at [docs.brinjal.dev](https://docs.brinjal.dev)

## Contributing

We welcome contributions! Please see our [contributing guidelines](https://github.com/sg-s/brinjal/blob/main/CONTRIBUTING.md) for details.

## License

Brinjal is licensed under the MIT License. See [LICENSE.txt](../LICENSE.txt) for details.
