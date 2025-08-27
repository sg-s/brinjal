# Task Development Guide

## Overview

This guide explains how to create and manage tasks in the Brinjal task system. The system uses semaphore-based concurrency control to efficiently manage both CPU-bound and I/O-bound tasks.

## Task Concurrency System

### Semaphore-Based Concurrency

Tasks use semaphores to control how many can run concurrently:

- **`"single"` semaphore**: Only one task can run at a time (CPU-bound tasks)
- **`"multiple"` semaphore**: Up to 10 tasks can run concurrently (I/O-bound tasks)  
- **`"default"` semaphore**: Fallback with limit of 3 concurrent tasks

### Task Status Flow

1. **`queued`** - Task is in the queue, waiting to be picked up by a worker
2. **`running`** - Task has acquired its semaphore and is executing
3. **`done`** - Task completed successfully
4. **`failed`** - Task encountered an error

## Creating a Task

### Basic Task Structure

```python
from dataclasses import dataclass
from .task import Task

@dataclass
class MyCustomTask(Task):
    """Custom task that does specific work"""
    
    # Set concurrency type based on task characteristics
    semaphore_name: str = "single"  # or "multiple" or "default"
    
    def run(self):
        """Synchronous method that does the actual work"""
        # Your task logic here
        pass
```

### Choosing the Right Semaphore

- **Use `"single"` for CPU-bound tasks**:
  - Heavy computation
  - Data processing
  - Machine learning inference
  - Example: `ExampleCPUTask` (simulates CPU work)

- **Use `"multiple"` for I/O-bound tasks**:
  - Network requests
  - File operations
  - Database queries
  - External API calls
  - Example: `ExampleIOTask` (simulates I/O work)

- **Use `"default"` for unknown or mixed workloads**:
  - Fallback option
  - Moderate concurrency (limit of 3)

### Task Configuration

```python
@dataclass
class MyTask(Task):
    # Required fields (inherited from Task)
    task_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None
    
    # Concurrency control
    semaphore_name: str = "multiple"  # Allow multiple concurrent executions
    
    # Progress tracking
    progress: int = 0
    update_sleep_time: float = 0.1  # How often to check for progress updates
    
    # UI display
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
    
    def run(self):
        """Implement your task logic here"""
        # Set display information
        self.heading = "My Custom Task"
        self.body = "Processing data..."
        
        # Update progress as work progresses
        for i in range(100):
            self.progress = i
            # Do some work...
            time.sleep(0.1)
        
        # Set final status
        self.status = "done"
        self.body = "Task completed successfully!"
```

## Progress Hooks

For tasks that need to read progress from external sources:

```python
def progress_hook(self):
    """Called periodically to update progress from external source"""
    try:
        # Read progress from file, API, etc.
        with open("progress.txt", "r") as f:
            self.progress = int(f.read().strip())
    except Exception as e:
        # Keep current progress if reading fails
        pass
```

## Best Practices

### 1. Choose Appropriate Concurrency

- **CPU-bound**: Use `"single"` to avoid overwhelming the system
- **I/O-bound**: Use `"multiple"` to maximize throughput
- **Unknown**: Use `"default"` as a safe middle ground

### 2. Progress Updates

- Update `self.progress` regularly during execution
- Use `progress_hook()` for external progress sources
- Set `update_sleep_time` based on how often progress changes

### 3. Error Handling

- Set `self.status = "failed"` on errors
- Put error details in `self.results`
- Clean up any temporary resources

### 4. Resource Management

- Release any acquired resources in finally blocks
- Clean up temporary files
- Close database connections

## Example Tasks

### CPU-Bound Task

```python
@dataclass
class DataProcessingTask(Task):
    semaphore_name: str = "single"  # CPU-intensive work
    
    def run(self):
        self.heading = "Processing Data"
        self.body = "Analyzing large dataset..."
        
        # Simulate CPU work
        for i in range(100):
            self.progress = i
            # Do heavy computation
            time.sleep(0.1)
        
        self.status = "done"
        self.body = "Analysis complete!"
```

### I/O-Bound Task

```python
@dataclass
class APITask(Task):
    semaphore_name: str = "multiple"  # Network I/O
    
    def run(self):
        self.heading = "API Request"
        self.body = "Fetching data from external API..."
        
        # Simulate API call
        time.sleep(0.5)
        self.progress = 50
        
        # Process response
        time.sleep(0.5)
        self.progress = 100
        
        self.status = "done"
        self.body = "Data fetched successfully!"
```

## Testing Your Tasks

Use the provided test framework to verify your tasks work correctly:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_semaphore_concurrency.py

# Run with verbose output
pytest -v tests/
```

## Monitoring and Debugging

- Check task status in the queue endpoint
- Monitor semaphore acquisition in logs
- Use SSE streams for real-time updates
- Verify concurrency limits are respected

## Performance Considerations

- **Single semaphore tasks**: Will queue up if many are submitted
- **Multiple semaphore tasks**: Can overwhelm external systems if not limited
- **Default semaphore**: Good balance for mixed workloads
- **Progress update frequency**: Balance between responsiveness and overhead
