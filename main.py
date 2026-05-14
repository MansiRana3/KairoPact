from __future__ import annotations

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logger import configure_logging
from app.v1.router import router as v1_router

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="KairoPact Assignment")
app.include_router(v1_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
