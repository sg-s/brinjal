from typing import Literal, Optional

from pydantic import BaseModel


class TaskUpdate(BaseModel):
    """Base model for task updates"""

    task_id: str
    task_type: str
    status: Literal["pending", "running", "done", "failed", "cancelled"] = "pending"
    progress: int
    img: Optional[str] = None
    heading: Optional[str] = None
    body: Optional[str] = None
