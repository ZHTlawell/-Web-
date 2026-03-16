"""Application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.api_routes import router as api_router
from app.routes.page_routes import router as page_router


STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(title="Runzo 测试执行平台", version="1.0.0")
    application.include_router(page_router)
    application.include_router(api_router)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return application


app = create_app()
