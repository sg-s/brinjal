"""Task management and execution logic"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from .models import TaskUpdate
from .task import Task

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
        self._worker_tasks = []  # List of worker tasks instead of single worker
        self._recurring_task = None
        self.loop = None
        # Queue SSE subscribers - map subscriber_id to notification queue
        self.queue_subscribers = {}

        # Semaphore management for concurrency control
        self.semaphores = {
            "single": asyncio.Semaphore(1),  # Only 1 CPU-bound task at a time
            "multiple": asyncio.Semaphore(10),  # Up to 10 I/O-bound tasks
            "default": asyncio.Semaphore(3),  # Default fallback limit
        }

        # Worker pool configuration
        self.max_workers = 20  # Maximum number of worker tasks

    async def start(self):  # this needs to be async
        """Start the worker loops"""
        if not self._worker_tasks:  # Only start if no workers are running
            self.loop = asyncio.get_running_loop()

            # Create multiple worker tasks
            for i in range(self.max_workers):
                worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
                self._worker_tasks.append(worker_task)

            self._recurring_task = asyncio.create_task(self._recurring_scheduler())

    async def stop(self):
        """Stop the worker loops"""
        # Stop all worker tasks
        if self._worker_tasks:
            for worker_task in self._worker_tasks:
                worker_task.cancel()

            # Wait for all workers to complete
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks.clear()

        if self._recurring_task:
            self._recurring_task.cancel()
            try:
                await self._recurring_task
            except asyncio.CancelledError:
                self._recurring_task = None
                raise

    async def _worker_loop(self, worker_id: str):
        """Background worker that processes tasks"""

        logger.info(f"Worker {worker_id} started")
        while True:
            try:
                logger.info(f"Worker {worker_id} waiting for next task...")

                # pick up a task from queue
                task: Task = await self.task_queue.get()
                logger.info(
                    f"Worker {worker_id} picked up task {task.task_id} ({task.__class__.__name__})"
                )

                # Get the appropriate semaphore for this task
                semaphore = self.semaphores.get(
                    task.semaphore_name, self.semaphores["default"]
                )

                # Acquire the semaphore before executing the task
                logger.info(
                    f"Worker {worker_id} acquiring semaphore '{task.semaphore_name}' for task {task.task_id}"
                )
                async with semaphore:
                    logger.info(
                        f"Worker {worker_id} acquired semaphore '{task.semaphore_name}' for task {task.task_id}"
                    )

                    # Update task status to running and acquire semaphore
                    task.status = "running"
                    task.started_at = datetime.now()
                    await task.notify_update()
                    self.task_store[task.task_id] = task

                    try:
                        logger.info(f"Worker {worker_id} executing task {task.task_id}")
                        await task.execute()
                        # Don't override status here - let the task set its own final status
                        logger.info(
                            f"Worker {worker_id} completed task {task.task_id} successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"Worker {worker_id} failed task {task.task_id} with error: {str(e)}",
                            exc_info=True,
                        )
                        task.status = "failed"
                        task.results = str(e)
                        # Send final update for failed tasks
                        await task.notify_update()
                    finally:
                        # Set completed_at if task was successful
                        if task.status == "done":
                            task.completed_at = datetime.now()
                            # Send final update with completed timestamp
                            await self._send_final_task_update(task)

                        # Don't send additional updates - let the task handle its own status
                        # The task should have already set its final status and sent the final update
                        logger.info(
                            f"Worker {worker_id} finished task {task.task_id} with status {task.status}"
                        )
                        self.task_queue.task_done()

                        logger.info(
                            f"Worker {worker_id} released semaphore '{task.semaphore_name}' for task {task.task_id}"
                        )
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Worker {worker_id} encountered error: {e}", exc_info=True
                )
                # Continue processing other tasks
                continue

    async def add_task_to_queue(self, task: Task) -> str:
        """Add a task to the queue and return the task ID"""
        logger.info(
            f"Adding task {task.task_id} of type {task.__class__.__name__} to queue"
        )

        # Set the loop reference for the task
        task.loop = self.loop

        # Set initial status to queued
        task.status = "queued"

        # put the task on the queue
        await self.task_queue.put(task)
        self.task_store[task.task_id] = task

        # Notify queue subscribers of new task
        await self._notify_queue_subscribers("task_added", task)

        logger.info(f"Task {task.task_id} added to queue successfully")
        return task.task_id

    async def _notify_queue_subscribers(
        self, event_type: str, task: Task = None, task_id: str = None
    ):
        """Notify all queue subscribers of queue changes"""
        if not self.queue_subscribers:
            return

        # Prepare the notification data
        if event_type == "task_added":
            notification = {
                "type": event_type,
                "task": {
                    "task_id": task.task_id,
                    "parent_id": task.parent_id,
                    "task_type": task.__class__.__name__,
                    "status": task.status,
                    "progress": task.progress,
                    "img": getattr(task, "img", None),
                    "heading": getattr(task, "heading", None),
                    "body": getattr(task, "body", None),
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                    "completed_at": task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                },
            }
        elif event_type == "task_removed":
            notification = {"type": event_type, "task_id": task_id}
        else:
            return

        # Send notification to all subscribers
        # Create a copy of the subscribers to avoid modification during iteration
        subscribers_to_notify = list(self.queue_subscribers.items())
        failed_subscribers = []

        for subscriber_id, queue in subscribers_to_notify:
            try:
                await queue.put(notification)
            except Exception as e:
                logger.error(f"Failed to notify subscriber {subscriber_id}: {e}")
                failed_subscribers.append(subscriber_id)

        # Remove failed subscribers after iteration
        for subscriber_id in failed_subscribers:
            self.queue_subscribers.pop(subscriber_id, None)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.task_store.get(task_id)

    async def remove_task_from_store(self, task_id: str):
        """Remove a task from the store and notify queue subscribers"""
        try:
            if task_id in self.task_store:
                task = self.task_store.pop(task_id)
                # Notify queue subscribers of removed task
                try:
                    await self._notify_queue_subscribers(
                        "task_removed", task_id=task_id
                    )
                except Exception as e:
                    # Log notification errors but don't fail the deletion
                    logger.warning(
                        f"Failed to notify subscribers of task removal {task_id}: {e}"
                    )

                logger.info(f"Task {task_id} removed from store")
                return task
            else:
                logger.warning(f"Attempted to remove non-existent task {task_id}")
                return None
        except Exception as e:
            logger.error(
                f"Error removing task {task_id} from store: {e}", exc_info=True
            )
            raise

    def get_all_tasks(self) -> List[dict]:
        """Get all tasks with their status and progress"""
        return [
            {
                "task_id": task.task_id,
                "parent_id": task.parent_id,
                "task_type": task.__class__.__name__,
                "status": task.status,
                "progress": task.progress,
                "img": getattr(task, "img", None),
                "heading": getattr(task, "heading", None),
                "body": getattr(task, "body", None),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
            }
            for task in self.task_store.values()
        ]

    def search_tasks_by_attributes(self, search_criteria: dict) -> List[str]:
        """Search for tasks by attribute/value pairs using exact matching.

        Args:
            search_criteria: Dictionary where keys are attribute names and values are expected values.
                           All criteria must match (AND logic).
                           Special case: 'task_type' will match against the class name.

        Returns:
            List of task IDs that match all the specified criteria.
            Returns empty list if no tasks match or if attributes don't exist.
        """
        if not search_criteria:
            return []

        matching_task_ids = []

        for task in self.task_store.values():
            matches_all_criteria = True

            for attribute, expected_value in search_criteria.items():
                # Handle special case for task_type
                if attribute == "task_type":
                    actual_value = task.__class__.__name__
                else:
                    # Check if the task has the attribute
                    if not hasattr(task, attribute):
                        matches_all_criteria = False
                        break
                    actual_value = getattr(task, attribute)

                # Compare values
                if actual_value != expected_value:
                    matches_all_criteria = False
                    break

            if matches_all_criteria:
                matching_task_ids.append(task.task_id)

        return matching_task_ids

    def get_sse_event_generator(self, task_id: str, request):
        """Get an SSE event generator for a specific task"""

        task = self.get_task(task_id)
        if not task:
            return None

        async def event_generator():
            """Event generator for a specific task"""

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
                started_at=task.started_at.isoformat() if task.started_at else None,
                completed_at=task.completed_at.isoformat()
                if task.completed_at
                else None,
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

    def get_queue_sse_event_generator(self, request):
        """Get an SSE event generator for queue updates"""

        async def event_generator():
            """Event generator for queue updates"""

            # Create a unique subscriber ID for this connection
            subscriber_id = id(request)
            self.queue_subscribers[subscriber_id] = asyncio.Queue()

            try:
                # Send initial queue state
                initial_tasks = self.get_all_tasks()
                yield f"data: {json.dumps({'type': 'queue_updated', 'tasks': initial_tasks})}\n\n"

                # Monitor for queue changes
                while True:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break

                    try:
                        # Wait for notifications with timeout
                        notification = await asyncio.wait_for(
                            self.queue_subscribers[subscriber_id].get(), timeout=30
                        )
                        yield f"data: {json.dumps(notification)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield ": keepalive\n\n"

            finally:
                # Remove subscriber when connection closes
                self.queue_subscribers.pop(subscriber_id, None)

        return event_generator

    async def _send_final_task_update(self, task: Task):
        """Send a final task update with the completed timestamp"""

        try:
            # Create a final update with the completed timestamp
            final_update = TaskUpdate(
                task_id=task.task_id,
                parent_id=task.parent_id,
                task_type=task.__class__.__name__,
                status=task.status,
                progress=task.progress,
                img=task.img,
                heading=task.heading,
                body=task.body,
                started_at=task.started_at.isoformat() if task.started_at else None,
                completed_at=task.completed_at.isoformat()
                if task.completed_at
                else None,
            )

            logger.info(
                f"Task {task.task_id} final update - status: {task.status}, completed_at: {task.completed_at}"
            )
            logger.info(f"Final update data: {final_update.model_dump()}")

            # Put the final update on the task's update queue
            await task.update_queue.put(final_update.model_dump())
            logger.info(
                f"Sent final update for task {task.task_id} with completed_at: {task.completed_at}"
            )
        except Exception as e:
            logger.error(f"Failed to send final update for task {task.task_id}: {e}")

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
