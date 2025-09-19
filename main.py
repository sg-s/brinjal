"""Main FastAPI application for brinjal"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.brinjal.api.router import router
from src.brinjal.manager import task_manager
from src.brinjal.task import ExampleCPUTask


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Set up task manager and recurring tasks on startup"""
    # Start the task manager
    await task_manager.start()

    # Create a template task for the recurring task (commented out to avoid interference)
    # recurring_template = ExampleCPUTask(
    #     name="Recurring Task (Every Minute)",
    #     sleep_time=0.05,  # Faster for demo purposes
    #     heading="🔄 Recurring Task",
    #     body="This task runs automatically every minute to demonstrate recurring task functionality",
    # )

    # # Add the recurring task (runs every minute)
    # recurring_id = await task_manager.add_recurring_task(
    #     cron_expression="*/1 * * * *",  # Every minute
    #     template_task=recurring_template,
    #     max_concurrent=1,  # Only one instance at a time
    # )

    # print(f"✅ Recurring task created with ID: {recurring_id}")
    # print("🔄 Recurring task will run every minute")

    yield  # App is running

    # Stop the task manager on shutdown
    await task_manager.stop()


app = FastAPI(
    title="Brinjal", description="🍆 Brinjal task management system", lifespan=lifespan
)

# Include the router
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
