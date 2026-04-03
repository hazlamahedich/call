from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import (
    health,
    webhooks,
    branding,
    clients,
    onboarding,
    usage,
    calls,
    webhooks_vapi,
    tts,
    telemetry,
)
from routers.ws_transcript import router as ws_transcript_router
from middleware.auth import AuthMiddleware
from config.settings import settings
from services.tts.factory import get_tts_orchestrator, shutdown_tts
from services.telemetry.worker import TelemetryWorker
from services.telemetry import telemetry_queue
from database.session import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    orchestrator = get_tts_orchestrator()
    await orchestrator.start_cleanup_task()

    # Start telemetry worker (Story 2.4)
    if settings.TELEMETRY_WORKER_ENABLED:
        telemetry_worker = TelemetryWorker(AsyncSessionLocal)
        await telemetry_queue.start_worker(telemetry_worker.process_batch)

    yield

    # Shutdown
    await shutdown_tts()

    # Stop telemetry worker
    if settings.TELEMETRY_WORKER_ENABLED:
        await telemetry_queue.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware, jwks_url=settings.CLERK_JWKS_URL)

app.include_router(health.router, tags=["Health"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(branding.router, tags=["Branding"])
app.include_router(clients.router, tags=["Clients"])
app.include_router(onboarding.router, tags=["Onboarding"])
app.include_router(usage.router, tags=["Usage"])
app.include_router(calls.router, tags=["Calls"])
app.include_router(webhooks_vapi.router, tags=["Vapi Webhooks"])
app.include_router(ws_transcript_router, tags=["WebSocket Transcription"])
app.include_router(tts.router, tags=["TTS"])
app.include_router(telemetry.router, tags=["Telemetry"])
