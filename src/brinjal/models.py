from typing import Literal, Optional

from pydantic import BaseModel


class TaskUpdate(BaseModel):
    """Base model for task updates"""

    task_id: str
    parent_id: Optional[str] = None  # What started this task
    task_type: str
    status: Literal["pending", "running", "done", "failed", "cancelled"] = "pending"
    progress: int
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
    started_at: Optional[str] = None  # ISO format timestamp when task started
    completed_at: Optional[str] = None  # ISO format timestamp when task completed
