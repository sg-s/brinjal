# Recurring Tasks

Brinjal supports recurring tasks that automatically execute at specified intervals using cron-like syntax. This feature allows you to set up automated workflows that run periodically without manual intervention.

## Overview

Recurring tasks in Brinjal are managed by the `TaskManager` and use the `croniter` library for flexible scheduling. Each recurring task configuration creates new task instances at the specified intervals, maintaining parent-child relationships for tracking and monitoring.

## Key Concepts

### RecurringTaskInfo

The `RecurringTaskInfo` class contains all the configuration and state information for a recurring task:

- **`recurring_id`**: Unique identifier for the recurring task configuration
- **`cron_expression`**: Cron expression defining when the task should run
- **`template_task`**: Fully configured task instance to clone from
- **`max_concurrent`**: Maximum number of instances that can run simultaneously
- **`enabled`**: Whether the recurring task is currently active

### Parent-Child Relationships

Every task in Brinjal now has a `parent_id` field that establishes relationships:

- **Regular tasks**: `parent_id` is `None`
- **Recurring task instances**: `parent_id` points to the recurring task configuration
- **Future task spawning**: Tasks can spawn child tasks with their own `task_id` as the parent

## Usage

### Adding a Recurring Task

```python
from brinjal.task import ExampleTask
from brinjal.manager import task_manager

# Create a fully configured task
backup_task = ExampleTask(
    sleep_time=0.1,
    heading="Daily Backup",
    body="Performing daily backup operation"
)

# Add as recurring task (runs every day at 2 AM)
recurring_id = await task_manager.add_recurring_task(
    cron_expression="0 2 * * *",
    template_task=backup_task,
    max_concurrent=1
)

print(f"Recurring task created with ID: {recurring_id}")
```

### Cron Expression Format

Brinjal uses standard cron syntax:

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
│ │ │ │ │
* * * * *
```

**Common Examples:**
- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 2 * * *` - Every day at 2 AM
- `0 9 * * 1` - Every Monday at 9 AM
- `0 0 1 * *` - First day of every month at midnight

### Managing Recurring Tasks

```python
# Get information about a recurring task
recurring_info = task_manager.get_recurring_task(recurring_id)

# Get all recurring tasks
all_recurring = task_manager.get_all_recurring_tasks()

# Disable a recurring task (stops scheduling new instances)
task_manager.disable_recurring_task(recurring_id)

# Re-enable a recurring task
task_manager.enable_recurring_task(recurring_id)

# Remove a recurring task configuration
task_manager.remove_recurring_task(recurring_id)
```

### Task Cloning

When a recurring task is scheduled to run, Brinjal creates a new instance by cloning the template task:

- **Shallow copy**: All attributes are copied from the template
- **New identifiers**: Each instance gets a unique `task_id`
- **Parent relationship**: `parent_id` is set to the recurring task ID
- **Fresh state**: New `update_queue` and execution state

## Advanced Features

### Concurrent Execution Control

```python
# Allow up to 3 instances to run simultaneously
recurring_id = await task_manager.add_recurring_task(
    cron_expression="*/1 * * * *",  # Every minute
    template_task=long_running_task,
    max_concurrent=3  # Up to 3 concurrent instances
)
```

This prevents resource exhaustion when tasks take longer than the interval to complete.

### Monitoring and Debugging

```python
# Get all tasks with their parent relationships
all_tasks = task_manager.get_all_tasks()

for task_info in all_tasks:
    if task_info["parent_id"]:
        print(f"Task {task_info['task_id']} is a child of recurring task {task_info['parent_id']}")
    else:
        print(f"Task {task_info['task_id']} is a standalone task")
```

### Task Updates with Parent Information

All task updates now include `parent_id` information, making it easy to trace the lineage of task executions:

```python
# In your task update handler
async def handle_task_update(update_data):
    if update_data["parent_id"]:
        print(f"Recurring task instance {update_data['task_id']} "
              f"from parent {update_data['parent_id']} updated: {update_data['status']}")
    else:
        print(f"Standalone task {update_data['task_id']} updated: {update_data['status']}")
```

## Best Practices

### 1. Template Task Configuration

Always fully configure your template task before adding it as recurring:

```python
# Good: Fully configured template
backup_task = BackupTask(
    source_path="/data",
    destination_path="/backup",
    compression_level=9,
    heading="Daily Backup",
    body="Automated daily backup process"
)

# Bad: Incomplete configuration
backup_task = BackupTask()  # Missing required parameters
```

### 2. Concurrent Execution Limits

Set appropriate `max_concurrent` values based on your resource constraints:

```python
# For resource-intensive tasks
await task_manager.add_recurring_task(
    cron_expression="0 2 * * *",  # Daily at 2 AM
    template_task=heavy_task,
    max_concurrent=1  # Only one instance at a time
)

# For lightweight tasks
await task_manager.add_recurring_task(
    cron_expression="*/5 * * * *",  # Every 5 minutes
    template_task=light_task,
    max_concurrent=5  # Multiple instances OK
)
```

### 3. Error Handling

Recurring tasks continue to run even if individual instances fail. Monitor the recurring task state:

```python
recurring_info = task_manager.get_recurring_task(recurring_id)
print(f"Total runs: {recurring_info.total_runs}")
print(f"Total failures: {recurring_info.total_failures}")
print(f"Consecutive failures: {recurring_info.consecutive_failures}")
```

### 4. Resource Cleanup

Remember that recurring tasks are ephemeral - they don't persist across application restarts. If you need persistent recurring tasks, implement configuration storage:

```python
# Store recurring task configurations
recurring_configs = [
    {
        "cron_expression": "0 2 * * *",
        "task_class": "BackupTask",
        "task_params": {"source": "/data", "dest": "/backup"}
    }
]

# Recreate recurring tasks on startup
for config in recurring_configs:
    task_class = getattr(importlib.import_module("brinjal.task"), config["task_class"])
    template_task = task_class(**config["task_params"])
    
    await task_manager.add_recurring_task(
        cron_expression=config["cron_expression"],
        template_task=template_task
    )
```

## Dependencies

Recurring tasks require the `croniter` package:

```bash
pip install croniter
```

Or add it to your project dependencies:

```toml
dependencies = [
    "croniter>=2.0.0",
    # ... other dependencies
]
```

## Limitations

- **Ephemeral**: Recurring task configurations don't persist across application restarts
- **Single parent**: Tasks can only have one direct parent (no grandparent relationships)
- **Clock dependency**: Scheduling depends on system clock accuracy
- **Memory usage**: Each recurring task configuration consumes memory for state tracking

## Future Enhancements

Planned improvements for recurring tasks:

- **Persistent storage**: Save recurring task configurations to disk/database
- **Advanced scheduling**: Support for timezone-aware scheduling and business hours
- **Retry policies**: Configurable retry behavior for failed recurring task instances
- **Metrics and monitoring**: Enhanced tracking of recurring task performance and health
