# Task Development Guide

This guide explains how to create custom tasks by extending the `Task` base class. You'll learn the fundamentals of task development and see practical examples.

## Understanding the Task Base Class

The `Task` class provides a foundation for all tasks in Brinjal. It handles:

- **Task lifecycle management** (pending → running → done/failed)
- **Progress tracking** (0-100%)
- **Real-time updates** via Server-Sent Events
- **Asynchronous execution** coordination
- **Metadata management** (img, heading, body)

## Basic Task Structure

```python
from brinjal.task import Task
from dataclasses import dataclass

@dataclass
class MyCustomTask(Task):
    # Add your custom fields here
    custom_param: str = ""
    
    def run(self):
        """Implement your synchronous work here"""
        # Your task logic goes here
        pass
```

## The `run()` Method

The `run()` method is where you implement your actual work. It should be **synchronous** because it runs in a separate thread to avoid blocking the event loop.

### Key Points About `run()`:

1. **Must be synchronous** - No `async/await` keywords
2. **Runs in a thread** - Use `asyncio.to_thread()` for I/O operations
3. **Update progress** - Set `self.progress` to trigger updates
4. **Set final status** - Use `self.status = "done"` or `"failed"`
5. **Handle exceptions** - The base class will catch and mark as failed

## Simple Example: Counter Task

```python
from brinjal.task import Task
from dataclasses import dataclass
import time

@dataclass
class CounterTask(Task):
    count_to: int = 10
    
    def run(self):
        """Count from 0 to count_to with progress updates"""
        self.heading = f"Counting to {self.count_to}"
        self.body = "Incrementing counter..."
        
        for i in range(self.count_to + 1):
            self.progress = int((i / self.count_to) * 100)
            time.sleep(0.5)  # Simulate work
        
        self.status = "done"
        self.body = f"Counted to {self.count_to} successfully!"
```

## Advanced Example: File Processing Task

```python
from brinjal.task import Task
from dataclasses import dataclass
import os
import time

@dataclass
class FileProcessingTask(Task):
    file_path: str = ""
    operation: str = "copy"  # copy, move, delete
    
    def run(self):
        """Process a file with progress updates"""
        if not os.path.exists(self.file_path):
            self.status = "failed"
            self.body = f"File not found: {self.file_path}"
            return
        
        file_size = os.path.getsize(self.file_path)
        self.heading = f"{self.operation.title()} File"
        self.body = f"Processing {os.path.basename(self.file_path)}"
        
        # Simulate file processing with progress
        for i in range(101):
            self.progress = i
            time.sleep(0.1)
        
        self.status = "done"
        self.body = f"File {self.operation} completed successfully"
```

## Working with External APIs

When your task needs to make HTTP requests or use external services:

```python
from brinjal.task import Task
from dataclasses import dataclass
import requests
import time

@dataclass
class APITask(Task):
    url: str = ""
    method: str = "GET"
    
    def run(self):
        """Make API request with progress updates"""
        self.heading = f"{self.method} Request"
        self.body = f"Calling {self.url}"
        
        try:
            # Simulate API call preparation
            self.progress = 10
            time.sleep(0.5)
            
            # Make the actual request
            self.progress = 50
            response = requests.request(self.method, self.url, timeout=30)
            
            # Process response
            self.progress = 90
            time.sleep(0.5)
            
            if response.status_code == 200:
                self.status = "done"
                self.body = f"API call successful: {response.status_code}"
                self.results = response.json()
            else:
                self.status = "failed"
                self.body = f"API call failed: {response.status_code}"
                
        except Exception as e:
            self.status = "failed"
            self.body = f"Error: {str(e)}"
```

## Database Operations

For tasks that need database access:

```python
from brinjal.task import Task
from dataclasses import dataclass
import sqlite3
import time

@dataclass
class DatabaseTask(Task):
    query: str = ""
    db_path: str = "database.db"
    
    def run(self):
        """Execute database query with progress updates"""
        self.heading = "Database Operation"
        self.body = f"Executing: {self.query[:50]}..."
        
        try:
            # Connect to database
            self.progress = 20
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Execute query
            self.progress = 60
            cursor.execute(self.query)
            
            # Commit changes
            self.progress = 80
            conn.commit()
            
            # Clean up
            self.progress = 90
            cursor.close()
            conn.close()
            
            self.status = "done"
            self.body = "Database operation completed successfully"
            
        except Exception as e:
            self.status = "failed"
            self.body = f"Database error: {str(e)}"
```

## Long-Running Tasks

For tasks that take a long time, provide meaningful progress updates:

```python
from brinjal.task import Task
from dataclasses import dataclass
import time

@dataclass
class LongRunningTask(Task):
    duration_seconds: int = 60
    
    def run(self):
        """Long-running task with detailed progress"""
        self.heading = "Long Running Process"
        self.body = f"Running for {self.duration_seconds} seconds"
        
        start_time = time.time()
        target_time = start_time + self.duration_seconds
        
        while time.time() < target_time:
            elapsed = time.time() - start_time
            progress = int((elapsed / self.duration_seconds) * 100)
            
            if progress != self.progress:
                self.progress = progress
                self.body = f"Elapsed: {elapsed:.1f}s / {self.duration_seconds}s"
            
            time.sleep(0.1)
        
        self.progress = 100
        self.status = "done"
        self.body = "Long running process completed!"
```

## Error Handling

Always handle errors gracefully in your `run()` method:

```python
from brinjal.task import Task
from dataclasses import dataclass
import time

@dataclass
class RobustTask(Task):
    operation: str = "default"
    
    def run(self):
        """Task with comprehensive error handling"""
        try:
            self.heading = f"Robust {self.operation}"
            self.body = "Starting operation..."
            
            # Simulate work
            for i in range(10):
                self.progress = i * 10
                time.sleep(0.5)
                
                # Simulate potential failure
                if i == 5 and self.operation == "risky":
                    raise ValueError("Simulated failure at step 5")
            
            self.status = "done"
            self.body = "Operation completed successfully"
            
        except Exception as e:
            self.status = "failed"
            self.body = f"Operation failed: {str(e)}"
            # You can also set additional error details
            self.results = {"error": str(e), "step": "unknown"}
```

## Best Practices

### 1. **Progress Updates**
- Update progress frequently for long tasks
- Use meaningful progress values (0-100)
- Avoid overwhelming the update queue

### 2. **Status Management**
- Always set final status (`done`, `failed`, or `cancelled`)
- Provide meaningful error messages
- Use `self.body` for detailed status information

### 3. **Resource Management**
- Clean up resources in your `run()` method
- Handle exceptions gracefully
- Don't leave connections open

### 4. **Performance**
- Keep the `run()` method efficient
- Use `time.sleep()` sparingly
- Consider breaking long tasks into smaller steps

### 5. **User Experience**
- Provide clear headings and descriptions
- Update progress meaningfully
- Give helpful error messages

## Testing Your Tasks

### 1. **Create a Test Task**

```python
from brinjal.task import Task
from dataclasses import dataclass
import time

@dataclass
class TestTask(Task):
    test_param: str = "test"
    
    def run(self):
        """Test task for development"""
        self.heading = "Test Task"
        self.body = f"Testing with: {self.test_param}"
        
        for i in range(5):
            self.progress = i * 20
            time.sleep(1)
        
        self.status = "done"
        self.body = "Test completed successfully"
```

### 2. **Test in Development**

```bash
# Start the server
make dev

# Create your test task
curl -X POST "http://localhost:8000/api/tasks/test_task" \
  -H "Content-Type: application/json" \
  -d '{"test_param": "hello world"}'

# Monitor progress
curl "http://localhost:8000/api/tasks/queue"
```

## Next Steps

Now that you understand task development:

1. [Explore the API reference](./api-reference.md) for more details
2. [Learn about integration](./integration.md) in your projects
3. [Check out examples](./examples.md) for more use cases
4. [Understand the web component](./web-component.md) for displaying tasks

## Summary

Creating custom tasks in Brinjal is straightforward:

1. **Inherit from `Task`** class
2. **Implement the `run()` method** with your logic
3. **Update progress** during execution
4. **Set final status** when complete
5. **Handle errors** gracefully

The base class handles all the complexity of task management, progress tracking, and real-time updates. You focus on your business logic!
