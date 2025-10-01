"""Tests for error handling functionality in tasks."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from brinjal.manager import TaskManager
from brinjal.task import ExampleCPUTask, Task


class FailingTask(Task):
    """Test task that always fails with a specific error."""

    def run(self):
        raise ValueError("This is a test error")


class TestErrorHandling:
    """Test cases for error handling functionality."""

    def test_capture_error_method(self):
        """Test that capture_error method properly captures error information."""
        task = ExampleCPUTask()

        # Create a test exception
        test_exception = ValueError("Test error message")

        # Capture the error
        task.capture_error(test_exception)

        # Verify error information was captured
        assert task.error_type == "ValueError"
        assert task.error_message == "Test error message"
        # Should contain the exception information
        assert "ValueError: Test error message" in task.error_traceback
        assert task.status == "failed"

    def test_execute_handles_exceptions(self):
        """Test that execute method properly handles exceptions from run()."""
        task = FailingTask()

        # Run execute in an event loop
        async def run_test():
            with pytest.raises(ValueError):
                await task.execute()

            # Verify error information was captured
            assert task.status == "failed"
            assert task.error_type == "ValueError"
            assert task.error_message == "This is a test error"
            assert "ValueError: This is a test error" in task.error_traceback
            assert "Task failed: This is a test error" in task.body

        asyncio.run(run_test())

    def test_notify_update_includes_error_info(self):
        """Test that notify_update includes error information in the update."""
        task = ExampleCPUTask()
        task.capture_error(ValueError("Test error"))

        # Mock the update queue
        task.update_queue = AsyncMock()

        # Run notify_update
        async def run_test():
            await task.notify_update()

            # Verify the update was sent with error information
            task.update_queue.put.assert_called_once()
            update_data = task.update_queue.put.call_args[0][0]

            assert update_data["error_type"] == "ValueError"
            assert update_data["error_message"] == "Test error"
            # Should contain the exception information
            assert "ValueError: Test error" in update_data["error_traceback"]

        asyncio.run(run_test())

    def test_failure_probability_with_error_handling(self):
        """Test that failure probability works with error handling."""
        task = ExampleCPUTask(failure_probability=1.0, sleep_time=0.01)

        async def run_test():
            with pytest.raises(Exception):
                await task.execute()

            # Verify error information was captured
            assert task.status == "failed"
            assert task.error_type == "Exception"
            assert "Task failed with probability 1.0" in task.error_message
            assert "Task failed with probability 1.0" in task.error_traceback
            # The task's run() method sets the body, not the error handler
            assert "Task failed due to failure probability" in task.body

        asyncio.run(run_test())

    def test_task_manager_error_handling(self):
        """Test that TaskManager properly handles task errors."""
        manager = TaskManager()
        task = FailingTask()

        async def run_test():
            # Add task to queue
            task_id = await manager.add_task_to_queue(task)

            # Start the manager
            await manager.start()

            # Wait a bit for the task to be processed
            await asyncio.sleep(0.1)

            # Get the task from the store
            stored_task = manager.get_task(task_id)

            # Verify error information was captured
            assert stored_task is not None
            assert stored_task.status == "failed"
            assert stored_task.error_type == "ValueError"
            assert stored_task.error_message == "This is a test error"
            assert "ValueError: This is a test error" in stored_task.error_traceback
            assert (
                stored_task.results == "This is a test error"
            )  # Backward compatibility

            # Stop the manager
            try:
                await manager.stop()
            except asyncio.CancelledError:
                # Expected when stopping the manager
                pass

        asyncio.run(run_test())

    def test_error_traceback_format(self):
        """Test that error traceback is properly formatted."""
        task = ExampleCPUTask()

        def failing_function():
            raise RuntimeError("Nested error")

        def calling_function():
            failing_function()

        try:
            calling_function()
        except RuntimeError as e:
            task.capture_error(e)

        # Verify traceback contains the full stack
        assert "RuntimeError: Nested error" in task.error_traceback
        assert "failing_function()" in task.error_traceback
        assert "calling_function()" in task.error_traceback

    def test_multiple_error_captures(self):
        """Test that multiple error captures work correctly."""
        task = ExampleCPUTask()

        # Capture first error
        task.capture_error(ValueError("First error"))
        first_error_type = task.error_type
        first_error_message = task.error_message

        # Capture second error
        task.capture_error(RuntimeError("Second error"))

        # Verify second error overwrote first
        assert task.error_type == "RuntimeError"
        assert task.error_message == "Second error"
        assert task.error_type != first_error_type
        assert task.error_message != first_error_message

    def test_error_handling_with_progress_updates(self):
        """Test that error handling works with progress updates."""
        task = ExampleCPUTask(failure_probability=1.0, sleep_time=0.01)

        # Mock the update queue to track updates
        task.update_queue = AsyncMock()

        async def run_test():
            with pytest.raises(Exception):
                await task.execute()

            # Verify multiple updates were sent (including error update)
            assert task.update_queue.put.call_count >= 2

            # Get the last update (should be the error update)
            last_update = task.update_queue.put.call_args_list[-1][0][0]
            assert last_update["status"] == "failed"
            assert last_update["error_type"] == "Exception"

        asyncio.run(run_test())

    def test_error_handling_preserves_task_state(self):
        """Test that error handling preserves other task state."""
        task = ExampleCPUTask(
            name="Test Task", failure_probability=1.0, sleep_time=0.01
        )
        task.heading = "Test Heading"
        task.body = "Test Body"
        task.progress = 50

        async def run_test():
            with pytest.raises(Exception):
                await task.execute()

            # Verify error information was captured
            assert task.status == "failed"
            assert task.error_type == "Exception"

            # Verify other state was preserved
            assert task.name == "Test Task"
            # The task's run() method sets heading to the task name
            assert task.heading == "Test Task"
            # Body is set by the task's run() method, not error handler
            assert "Task failed due to failure probability" in task.body
            # Progress is set by the task's run() method during startup
            assert task.progress == -1  # Task sets progress to -1 during startup

        asyncio.run(run_test())
