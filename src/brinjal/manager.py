"""Task management and execution logic"""

import asyncio
import json
from typing import List, Optional, Dict
from datetime import datetime
import logging
from dataclasses import dataclass, field
from uuid import uuid4

from .task import Task
from .models import TaskUpdate

logger = logging.getLogger(__name__)


@dataclass
class RecurringTaskInfo:
    """Information about a recurring task configuration"""

    cron_expression: str
    template_task: Task  # Fully configured task instance to clone from
    recurring_id: str = field(default_factory=lambda: str(uuid4()))
    max_concurrent: int = 1
    enabled: bool = True

    # State tracking
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    consecutive_failures: int = 0
    total_runs: int = 0
    total_failures: int = 0

    created_at: datetime = field(default_factory=datetime.now)


class TaskManager:
    """Manages task queue and execution"""

    def __init__(self):
        self.task_queue = asyncio.Queue()
        self.task_store = {}
        self.recurring_tasks: Dict[str, RecurringTaskInfo] = {}
        self._worker_task = None
        self._recurring_task = None
        self.loop = None

    async def start(self):  # this needs to be async
        """Start the worker loop"""
        if self._worker_task is None:
            self.loop = asyncio.get_running_loop()
            self._worker_task = asyncio.create_task(self._worker_loop())
            self._recurring_task = asyncio.create_task(self._recurring_scheduler())

    async def stop(self):
        """Stop the worker loop"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                self._worker_task = None
                raise

        if self._recurring_task:
            self._recurring_task.cancel()
            try:
                await self._recurring_task
            except asyncio.CancelledError:
                self._recurring_task = None
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
                "parent_id": task.parent_id,
                "task_type": task.__class__.__name__,
                "status": task.status,
                "progress": task.progress,
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
                parent_id=task.parent_id,
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
                    if update["status"] in ("done", "failed", "cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"

        return event_generator

    async def add_recurring_task(
        self,
        cron_expression: str,
        template_task: Task,
        max_concurrent: int = 1,
    ) -> str:
        """Add a recurring task that will be re-queued based on cron expression"""

        recurring_info = RecurringTaskInfo(
            cron_expression=cron_expression,
            template_task=template_task,
            max_concurrent=max_concurrent,
            next_run=self._calculate_next_run(cron_expression),
        )

        self.recurring_tasks[recurring_info.recurring_id] = recurring_info

        # Create and queue initial task instance
        initial_task = self._clone_task(template_task, recurring_info.recurring_id)
        await self.add_task_to_queue(initial_task)

        return recurring_info.recurring_id

    def get_recurring_task(self, recurring_id: str) -> Optional[RecurringTaskInfo]:
        """Get recurring task info by ID"""
        return self.recurring_tasks.get(recurring_id)

    def get_all_recurring_tasks(self) -> List[RecurringTaskInfo]:
        """Get all recurring task configurations"""
        return list(self.recurring_tasks.values())

    def disable_recurring_task(self, recurring_id: str) -> bool:
        """Disable a recurring task"""
        if recurring_id in self.recurring_tasks:
            self.recurring_tasks[recurring_id].enabled = False
            return True
        return False

    def enable_recurring_task(self, recurring_id: str) -> bool:
        """Enable a recurring task"""
        if recurring_id in self.recurring_tasks:
            self.recurring_tasks[recurring_id].enabled = True
            return True
        return False

    def remove_recurring_task(self, recurring_id: str) -> bool:
        """Remove a recurring task configuration"""
        return self.recurring_tasks.pop(recurring_id, None) is not None

    def _clone_task(self, template_task: Task, parent_id: str) -> Task:
        """Create a new task instance from a template using shallow copy"""

        # Shallow copy all attributes
        new_task = type(template_task)(
            **{
                k: v
                for k, v in template_task.__dict__.items()
                if k not in ["task_id", "parent_id", "update_queue"]
            }
        )

        # Set new task_id and parent relationship
        new_task.task_id = str(uuid4())
        new_task.parent_id = parent_id

        # Create fresh update queue
        new_task.update_queue = asyncio.Queue()

        return new_task

    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate the next run time based on cron expression"""

        from croniter import croniter

        return croniter(cron_expression, datetime.now()).get_next(datetime)

    def _can_run_recurring_task(
        self, recurring_id: str, recurring_info: RecurringTaskInfo
    ) -> bool:
        """Check if a recurring task can run (not disabled, within concurrent limits)"""
        if not recurring_info.enabled:
            return False

        # Count currently running instances of this recurring task
        running_count = sum(
            1
            for task in self.task_store.values()
            if task.parent_id == recurring_id and task.status == "running"
        )

        return running_count < recurring_info.max_concurrent

    async def _recurring_scheduler(self):
        """Background task that handles recurring task scheduling"""
        logger.info("Recurring task scheduler started")

        while True:
            try:
                now = datetime.now()

                for recurring_id, recurring_info in self.recurring_tasks.items():
                    if (
                        recurring_info.next_run
                        and now >= recurring_info.next_run
                        and self._can_run_recurring_task(recurring_id, recurring_info)
                    ):
                        # Create and queue new task instance
                        new_task = self._clone_task(
                            recurring_info.template_task, recurring_id
                        )
                        await self.add_task_to_queue(new_task)

                        # Update recurring task state
                        recurring_info.last_run = now
                        recurring_info.total_runs += 1
                        recurring_info.next_run = self._calculate_next_run(
                            recurring_info.cron_expression
                        )

                        logger.info(
                            f"Scheduled recurring task {recurring_id} for execution"
                        )

                await asyncio.sleep(1)  # Check every second

            except Exception as e:
                logger.error(f"Error in recurring scheduler: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait longer on error


# Global task manager instance
task_manager = TaskManager()
