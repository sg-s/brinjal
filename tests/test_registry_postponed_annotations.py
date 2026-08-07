"""Registry tests for postponed annotation evaluation (PEP 563)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_origin

from brinjal.api.router import _create_request_model
from brinjal.registry import TaskRegistry
from brinjal.task import Task


@dataclass(kw_only=True)
class PostponedLiteralTask(Task):
    """Task whose fields use stringified annotations via ``__future__`` annotations."""

    media_type: Literal["movies", "tv"]
    tmdb_id: int
    semaphore_name: str = "multiple"


def test_registry_resolves_postponed_literal_field_types() -> None:
    """get_route_params must resolve Literal fields, not leave them as strings."""
    reg = TaskRegistry()
    params = {p["name"]: p for p in reg.get_route_params(PostponedLiteralTask)}

    assert get_origin(params["media_type"]["type"]) is Literal
    assert params["media_type"]["type"] == Literal["movies", "tv"]
    assert params["tmdb_id"]["type"] is int
    assert params["semaphore_name"]["type"] is str


def test_request_model_validates_postponed_literal_task() -> None:
    """Auto-generated Pydantic request models must accept postponed Literal fields."""
    reg = TaskRegistry()
    params = reg.get_route_params(PostponedLiteralTask)
    model = _create_request_model(PostponedLiteralTask, params)
    assert model is not None
    parsed = model.model_validate({"media_type": "movies", "tmdb_id": 2433})
    assert parsed.media_type == "movies"
    assert parsed.tmdb_id == 2433
