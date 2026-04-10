# Integrating Brinjal into a FastAPI app

This guide shows how to wire Brinjal’s task manager and routes into a FastAPI application so tasks run in the background and are exposed via HTTP.

## 1. Start and stop the task manager (lifespan)

The task manager runs worker loops and (optionally) the recurring scheduler. You must **start** it when the app starts and **stop** it when the app shuts down. Use FastAPI’s **lifespan** for this.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

from brinjal.manager import task_manager
from brinjal.api.router import router as brinjal_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start task manager on startup, stop on shutdown."""
    await task_manager.start()
    yield  # App is running
    await task_manager.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(brinjal_router, prefix="/api/tasks")
```

If you don’t call `task_manager.start()`, tasks will stay queued and never run. If you don’t call `task_manager.stop()` on shutdown, worker loops may not exit cleanly.

## 2. Mount the Brinjal router

Include Brinjal’s router so your app gets the task endpoints:

```python
from brinjal.api.router import router as brinjal_router

# Optional: use a prefix so all task routes live under /api/tasks
app.include_router(brinjal_router, prefix="/api/tasks")
```

With `prefix="/api/tasks"` you get, for example:

- `POST /api/tasks/example_cpu_task` – create and queue a task  
- `GET /api/tasks/queue` – list all tasks  
- `GET /api/tasks/{task_id}/stream` – SSE stream for a task’s progress  
- `GET /api/tasks/queue/stream` – SSE stream for queue add/remove events  
- `GET /api/tasks/recurring` – list recurring tasks  
- `POST /api/tasks/recurring/{task_type}` – create a recurring task  

Exact route paths for “create task” depend on [task registration](#3-register-your-own-tasks-optional).

## 3. Register your own tasks (optional)

Brinjal’s router is built from a **task registry**. When you import `brinjal.api.router`, it calls `register_task_routes()` and generates one POST route per **currently registered** task class. Built-in tasks (`ExampleCPUTask`, `ExampleIOTask`) are registered inside Brinjal. To expose **your** task classes as POST endpoints:

1. Define your task (subclass `Task`, use `@dataclass`, implement `run()`). See [Task Development](task-development.md#creating-a-new-task).
2. **Register before importing the router.** Routes are fixed at router import time, so register in a module that runs first:

```python
# myapp/tasks.py
from brinjal.registry import registry
from brinjal.task import Task
from dataclasses import dataclass

@dataclass
class MyBackupTask(Task):
    def run(self):
        ...

@dataclass
class MySyncTask(Task):
    def run(self):
        ...

registry.register(MyBackupTask)
registry.register(MySyncTask)
```

```python
# myapp/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

import myapp.tasks  # Registers MyBackupTask, MySyncTask
from brinjal.manager import task_manager
from brinjal.api.router import router as brinjal_router  # Import after registration


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_manager.start()
    yield
    await task_manager.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(brinjal_router, prefix="/api/tasks")
```

You then get `POST /api/tasks/my_backup_task` and `POST /api/tasks/my_sync_task` (class names are converted to snake_case paths). If you don’t register custom tasks, only the built-in example tasks get create endpoints; you can still enqueue tasks in code with `task_manager.add_task_to_queue(my_task)`.

## 4. Minimal full example

```python
# app.py
from contextlib import asynccontextmanager
from dataclasses import dataclass
from fastapi import FastAPI

from brinjal.manager import task_manager
from brinjal.api.router import router as brinjal_router
from brinjal.registry import registry
from brinjal.task import Task


@dataclass
class HelloTask(Task):
    def run(self):
        self.heading = "Hello"
        self.body = "Running..."
        self.progress = 50
        self.status = "done"


registry.register(HelloTask)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_manager.start()
    yield
    await task_manager.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(brinjal_router, prefix="/api/tasks")
```

Run with `uvicorn app:app --reload`. Then:

- `POST /api/tasks/hello_task` creates a task and returns `{"task_id": "..."}`.  
- `GET /api/tasks/{task_id}/stream` streams progress until the task is done or failed.

## 5. Recurring tasks in your app

To schedule a task on a cron, create a **template** task instance and pass it to `add_recurring_task` in lifespan (or any async context after the manager has started):

```python
from brinjal.manager import task_manager
from brinjal.task import ExampleCPUTask

# In lifespan, after task_manager.start():
template = ExampleCPUTask(name="Nightly job", sleep_time=0.1)
recurring_id = await task_manager.add_recurring_task(
    cron_expression="0 2 * * *",  # 02:00 every day
    template_task=template,
    max_concurrent=1,
)
```

The first run happens at the next 02:00 after this call, not immediately when the app starts.

See [Recurring tasks](recurring-tasks.md) for cron format and management (enable/disable, list, remove).
