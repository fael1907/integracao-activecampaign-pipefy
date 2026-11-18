from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Recebe leads da ActiveCampaign e cria cards no Pipefy.",
    version="0.1.0",
)
app.include_router(webhooks_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "dry_run": settings.dry_run}
