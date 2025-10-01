# Error Handling in Brinjal

Brinjal provides comprehensive error handling and tracking for task execution failures. When a task fails, detailed error information is captured and made available through the API and UI.

## Error Tracking Fields

Each task includes the following error tracking fields:

- `error_type`: The type of exception that caused the failure (e.g., "ValueError", "RuntimeError")
- `error_message`: The error message from the exception
- `error_traceback`: The full stack trace as a string
- `status`: Set to "failed" when an error occurs

## How Error Handling Works

### 1. Exception Capture in Task Execution

When a task's `run()` method raises an exception, the `execute()` method automatically captures detailed error information:

```python
class MyTask(Task):
    def run(self):
        # This will be automatically caught and tracked
        raise ValueError("Something went wrong!")
```

The error information is captured using the `capture_error()` method:

```python
def capture_error(self, exception: Exception):
    """Capture detailed error information from an exception."""
    self.error_type = type(exception).__name__
    self.error_message = str(exception)
    self.error_traceback = traceback.format_exc()
    self.status = "failed"
```

### 2. Error Information in Updates

Error information is included in all task updates sent to the UI:

```python
{
    "task_id": "12345",
    "status": "failed",
    "error_type": "ValueError",
    "error_message": "Something went wrong!",
    "error_traceback": "Traceback (most recent call last):\n  File \"...\", line 1, in <module>\n    raise ValueError(\"Something went wrong!\")\nValueError: Something went wrong!",
    "body": "Task failed: Something went wrong!",
    # ... other fields
}
```

### 3. Manager-Level Error Handling

The TaskManager also provides fallback error handling in case the task doesn't capture errors properly:

```python
try:
    await task.execute()
except Exception as e:
    # Fallback error capture
    if not task.error_message:
        task.capture_error(e)
    # Store error message for backward compatibility
    task.results = task.error_message or str(e)
    await task.notify_update()
```

## Using Error Information

### 1. Programmatic Access

You can access error information directly from task objects:

```python
# Get a failed task
task = task_manager.get_task(task_id)

if task.status == "failed":
    print(f"Error Type: {task.error_type}")
    print(f"Error Message: {task.error_message}")
    print(f"Stack Trace:\n{task.error_traceback}")
```

### 2. API Access

Error information is available through the API:

```python
# Get all tasks
response = requests.get("http://localhost:8000/queue")
tasks = response.json()

# Find failed tasks
failed_tasks = [task for task in tasks if task["status"] == "failed"]

for task in failed_tasks:
    print(f"Task {task['task_id']} failed:")
    print(f"  Type: {task['error_type']}")
    print(f"  Message: {task['error_message']}")
    print(f"  Traceback: {task['error_traceback']}")
```

### 3. Search Failed Tasks

You can search for failed tasks using the search API:

```python
# Search for failed tasks
search_criteria = {"status": "failed"}
response = requests.post("http://localhost:8000/search", json=search_criteria)
failed_task_ids = response.json()["task_ids"]
```

## Error Handling Best Practices

### 1. Handle Specific Exceptions

In your task's `run()` method, handle specific exceptions when possible:

```python
class MyTask(Task):
    def run(self):
        try:
            # Risky operation
            result = some_risky_operation()
        except FileNotFoundError as e:
            # Handle specific error
            self.body = f"File not found: {e}"
            self.status = "failed"
            raise  # Re-raise to trigger error capture
        except Exception as e:
            # Handle unexpected errors
            self.body = f"Unexpected error: {e}"
            self.status = "failed"
            raise
```

### 2. Provide Meaningful Error Messages

Make your error messages descriptive:

```python
class MyTask(Task):
    def run(self):
        try:
            process_data()
        except ValueError as e:
            # Provide context
            raise ValueError(f"Data validation failed: {e}") from e
```

### 3. Monitor Error Patterns

Use the error information to identify patterns:

```python
# Get all failed tasks
failed_tasks = task_manager.search_tasks_by_attributes({"status": "failed"})

# Analyze error types
error_types = {}
for task_id in failed_tasks:
    task = task_manager.get_task(task_id)
    error_type = task.error_type
    error_types[error_type] = error_types.get(error_type, 0) + 1

print("Error frequency:", error_types)
```

## Testing Error Handling

### 1. Test Task Failures

Create test tasks that intentionally fail:

```python
class FailingTask(Task):
    def run(self):
        raise ValueError("Test error")

# Test the task
task = FailingTask()
await task.execute()

assert task.status == "failed"
assert task.error_type == "ValueError"
assert "Test error" in task.error_message
```

### 2. Test Error Recovery

Test that your application can handle task failures gracefully:

```python
# Add a failing task
task_id = await task_manager.add_task_to_queue(FailingTask())

# Wait for it to fail
await asyncio.sleep(1)

# Check error information
task = task_manager.get_task(task_id)
assert task.status == "failed"
assert task.error_type is not None
```

## UI Error Display

The TaskList component automatically displays error information for failed tasks:

- Failed tasks show with a red status indicator
- Error messages are displayed in the task body
- Full error details are available in the task details view
- Stack traces can be viewed for debugging

## Troubleshooting

### Common Issues

1. **Missing Error Information**: If error information is missing, check that the task's `run()` method is raising exceptions properly.

2. **Incomplete Stack Traces**: Stack traces are captured at the point where `capture_error()` is called. For the most complete trace, ensure exceptions are not caught and re-raised unnecessarily.

3. **Error Information Not Updating**: Make sure `notify_update()` is called after capturing error information.

### Debugging Failed Tasks

1. Check the task status: `task.status == "failed"`
2. Examine the error type: `task.error_type`
3. Read the error message: `task.error_message`
4. Review the stack trace: `task.error_traceback`

This comprehensive error handling system ensures that you have full visibility into task failures and can effectively debug and monitor your task execution.
