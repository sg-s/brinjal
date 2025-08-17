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
            # Check if progress has changed
            if self.progress != last_progress:
                await self.notify_update()
                last_progress = self.progress

            # Small delay to avoid overwhelming the update queue
            await asyncio.sleep(0.05)

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

    def run(self):
        """Synchronous function that does the actual work"""
        import time

        for i in range(100):
            self.progress = i
            time.sleep(self.sleep_time)

        self.progress = 100
        self.status = "done"
