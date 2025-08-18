from dataclasses import dataclass, field
from typing import Optional, Any
import asyncio
from uuid import uuid4
from .models import TaskUpdate
import logging

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Generic task base class"""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    progress: int = 0
    results: Optional[Any] = None
    update_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    loop: Optional[asyncio.AbstractEventLoop] = None
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
    update_sleep_time: float = 0.05

    def progress_hook(self):
        """Optional progress hook. Use this to update the progress of the task."""

        pass

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
            task_type=self.__class__.__name__,
            status=self.status,
            progress=self.progress,
            img=self.img,
            heading=self.heading,
            body=self.body,
        )

        # Log the update for debugging
        logger.info(f"Task {self.task_id} sending update: {update_data}")

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
        while not sync_task.done():
            self.progress_hook()

            # Check if progress has changed
            if self.progress != last_progress:
                await self.notify_update()
                last_progress = self.progress

            # Small delay to avoid overwhelming the update queue
            await asyncio.sleep(self.update_sleep_time)

        # Wait for the sync task to complete
        await sync_task

        # Send final status update
        await self.notify_update()

        logger.info(f"Task {self.task_id} completed with status: {self.status}")

    def run(self):
        """Synchronous function that does the actual work"""
        raise NotImplementedError("Subclasses must implement run()")


@dataclass
class ExampleTask(Task):
    """Example task that demonstrates proper task execution and updates"""

    sleep_time: float = 0.1
    update_sleep_time: float = 0.05  # Update every 50ms

    def run(self):
        """Synchronous function that does the actual work"""
        import time

        self.heading = "Example Task"
        self.body = "This is an example task. It will run for 10 seconds and update the progress every 0.1 seconds."

        for i in range(100):
            self.progress = i
            time.sleep(self.sleep_time)

        self.progress = 100
        self.status = "done"
        self.body = "Task completed successfully!"


@dataclass
class ProgressHookExampleTask(Task):
    """Example task that demonstrates proper task execution and updates with a progress hook"""

    sleep_time: float = 0.02
    progress_file: str = "task_progress.txt"
    update_sleep_time: float = 0.1  # Update every 100ms (slower updates)

    def progress_hook(self):
        """Progress hook that reads progress from a file and updates the task"""
        try:
            with open(self.progress_file, "r") as f:
                progress_value = int(f.read().strip())
                self.progress = progress_value
                logger.info(f"Progress hook read progress: {progress_value}%")
        except (FileNotFoundError, ValueError, IOError) as e:
            logger.warning(f"Could not read progress from file: {e}")
            # Keep current progress if file reading fails

    def run(self):
        """Synchronous function that writes progress to a file"""
        import time
        import os

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
