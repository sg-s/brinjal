"""Task management and execution logic"""

import asyncio
import json
from typing import List, Optional
import logging

from .task import Task
from .models import TaskUpdate

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages task queue and execution"""

    def __init__(self):
        self.task_queue = asyncio.Queue()
        self.task_store = {}
        self._worker_task = None
        self.loop = None

    async def start(self):  # this needs to be async
        """Start the worker loop"""
        if self._worker_task is None:
            self.loop = asyncio.get_running_loop()
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self):
        """Stop the worker loop"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                self._worker_task = None
                raise

    async def _worker_loop(self):
        """Background worker that processes tasks"""
        logger.info("Worker loop started")
        while True:
            logger.info("Worker waiting for next task...")

            # pick up a task from queue
            task: Task = await self.task_queue.get()
            logger.info(
                f"Worker picked up task {task.task_id} ({task.__class__.__name__})"
            )

            task.status = "running"
            await task.notify_update()
            self.task_store[task.task_id] = task

            try:
                logger.info(f"Worker executing task {task.task_id}")
                await task.execute()
                # Don't override status here - let the task set its own final status
                logger.info(f"Task {task.task_id} completed successfully")
            except Exception as e:
                logger.error(
                    f"Task {task.task_id} failed with error: {str(e)}", exc_info=True
                )
                task.status = "failed"
                task.results = str(e)
                # Send final update for failed tasks
                await task.notify_update()
            finally:
                # Don't send additional updates - let the task handle its own status
                # The task should have already set its final status and sent the final update
                logger.info(f"Task {task.task_id} finished with status {task.status}")
                self.task_queue.task_done()

    async def add_task_to_queue(self, task: Task) -> str:
        """Add a task to the queue and return the task ID"""
        logger.info(
            f"Adding task {task.task_id} of type {task.__class__.__name__} to queue"
        )

        # Set the loop reference for the task
        task.loop = self.loop

        # put the task on the queue
        await self.task_queue.put(task)
        self.task_store[task.task_id] = task
        logger.info(f"Task {task.task_id} added to queue successfully")
        return task.task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.task_store.get(task_id)

    def get_all_tasks(self) -> List[dict]:
        """Get all tasks with their status and progress"""
        return [
            {
                "task_id": task.task_id,
                "task_type": task.__class__.__name__,
                "status": task.status,
                "progress": task.progress,
                "results": task.results,
                # Extract specific data for display
                "video_id": getattr(task, "video_id", None),
                "channel_id": getattr(task, "channel_id", None),
            }
            for task in self.task_store.values()
        ]

    def get_sse_event_generator(self, task_id: str, request):
        """Get an SSE event generator for a specific task"""
        task = self.get_task(task_id)
        if not task:
            return None

        async def event_generator():
            # Send initial state using TaskUpdate model
            initial_update = TaskUpdate(
                task_id=task.task_id,
                task_type=task.__class__.__name__,
                status=task.status,
                progress=task.progress,
                img=task.img,
                heading=task.heading,
                body=task.body,
            )

            # Yield initial state
            yield f"data: {json.dumps(initial_update.model_dump())}\n\n"

            # Monitor the task's update queue for changes
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    update = await asyncio.wait_for(task.update_queue.get(), timeout=10)
                    yield f"data: {json.dumps(update)}\n\n"

                    # If the task is done or failed, break and end the stream
                    if update["status"] in ("done", "failed"):
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"

        return event_generator


# Global task manager instance
task_manager = TaskManager()
