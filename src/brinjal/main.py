"""Main FastAPI application for brinjal"""

from fastapi import FastAPI

from .api.router import router

app = FastAPI(title="Brinjal", description="🍆 Brinjal task management system")

# Include the router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
