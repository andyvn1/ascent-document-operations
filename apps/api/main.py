"""FastAPI application entrypoint.

Run locally with: uvicorn apps.api.main:app --reload
"""

import logging

from fastapi import FastAPI

from apps.api.routes import documents
from ascent.shared import model_registry  # noqa: F401
from ascent.shared.config import get_settings
from ascent.shared.logging import configure_logging

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ascent Document Operations")
app.include_router(documents.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


logger.info("Application started in %s mode", settings.app_env)