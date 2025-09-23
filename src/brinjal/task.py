"""Task base class and examples Tasks."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from .models import TASK_STATES, TaskUpdate


@dataclass
class Task:
    """Generic task base class"""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None  # What started this task
    status: TASK_STATES = "queued"
    progress: int = 0
    results: Optional[Any] = None
    update_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    loop: Optional[asyncio.AbstractEventLoop] = None
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
    update_sleep_time: float = 0.05

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    semaphore_name: str = "default"

    def progress_hook(self):
        """Hook method for subclasses to inject custom progress logic.

        This method is called before checking if progress has changed.
        Subclasses can override this to read progress from external sources
        (like log files, APIs, etc.) and update self.progress.
        """
        pass

    async def notify_update(self):
        """Generic notify_update method that sends task status to the update queue"""
        update_data = TaskUpdate(
            task_id=self.task_id,
            parent_id=self.parent_id,
            task_type=self.__class__.__name__,
            status=self.status,
            progress=self.progress,
            img=self.img,
            heading=self.heading,
            body=self.body,
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
        )

        # Serialize the model before putting it on the queue
        await self.update_queue.put(update_data.model_dump())

    async def execute(self):
        """Generic run method that handles common task execution patterns"""
        self.status = "running"
        self.progress = 0

        # Send initial status update
        await self.notify_update()

        sync_task = asyncio.create_task(asyncio.to_thread(self.run))

        # Monitor progress and send updates
        last_progress = 0
        last_body = self.body
        last_heading = self.heading
        last_img = self.img
        last_status = self.status
        while not sync_task.done():
            self.progress_hook()

            # Check if progress has changed
            if (
                self.progress != last_progress
                or self.body != last_body
                or self.heading != last_heading
                or self.img != last_img
                or self.status != last_status
            ):
                await self.notify_update()
                last_progress = self.progress
                last_body = self.body
                last_heading = self.heading
                last_img = self.img
                last_status = self.status

            # Small delay to avoid overwhelming the update queue
            await asyncio.sleep(self.update_sleep_time)

        # Wait for the sync task to complete
        await sync_task

        # Set completed_at if task was successful
        if self.status == "done":
            self.completed_at = datetime.now()

        # Send final status update
        await self.notify_update()

    def run(self):
        """Synchronous function that does the actual work"""
        raise NotImplementedError("Subclasses must implement run()")


@dataclass
class ExampleCPUTask(Task):
    """Example task that demonstrates proper task execution and updates.
    This mimics a CPU-bound task. Only one can run at a time,
    because it uses the 'single' semaphore."""

    sleep_time: float = 0.1
    update_sleep_time: float = 0.05  # Update every 50ms
    semaphore_name: str = "single"  # CPU-bound task - only one can run at a time

    # optional arg
    name: str = "Example Task"

    def run(self):
        """Synchronous function that does the actual work"""
        import time

        self.body = "This is an example task. It will run for 10 seconds and update the progress every 0.1 seconds."

        self.heading = "Starting up..."
        self.progress = -1
        time.sleep(3)

        self.heading = self.name

        for i in range(100):
            self.progress = i
            time.sleep(self.sleep_time)

        self.progress = 100
        self.status = "done"
        self.body = "Task completed successfully!"


@dataclass
class ExampleIOTask(Task):
    """Example task that demonstrates proper task execution and updates with a progress hook. This task is I/O-bound and can run concurrently."""

    sleep_time: float = 0.02
    progress_file: str = "task_progress.txt"
    update_sleep_time: float = 0.1  # Update every 100ms (slower updates)
    semaphore_name: str = "multiple"  # I/O-bound task - multiple can run concurrently

    def progress_hook(self):
        """Progress hook that reads progress from a file and updates the task"""
        try:
            with open(self.progress_file, "r") as f:
                progress_value = int(f.read().strip())
                self.progress = progress_value
        except (FileNotFoundError, ValueError, IOError) as e:
            # Keep current progress if file reading fails
            pass

    def run(self):
        """Synchronous function that writes progress to a file"""
        import os
        import time

        self.heading = "Progress Hook Example Task"
        self.body = "This is a progress hook example task. The progress is written to a file and read from it."

        # Clear any existing progress file
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)

        for i in range(100):
            # Write current progress to file
            with open(self.progress_file, "w") as f:
                f.write(str(i))

            time.sleep(self.sleep_time)

        # Write final progress
        with open(self.progress_file, "w") as f:
            f.write("100")

        self.progress = 100
        self.status = "done"
        self.body = "Task completed successfully!"

        # Clean up progress file
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
