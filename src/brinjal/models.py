"""Types and models for the brinjal project."""

from typing import Literal, Optional

from pydantic import BaseModel

TASK_STATES = Literal["queued", "running", "done", "failed"]


class TaskUpdate(BaseModel):
    """Base model for task updates"""

    task_id: str
    parent_id: Optional[str] = None  # What started this task
    task_type: str
    status: TASK_STATES = "queued"
    progress: int
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
    started_at: Optional[str] = None  # ISO format timestamp when task started
    completed_at: Optional[str] = None  # ISO format timestamp when task completed
