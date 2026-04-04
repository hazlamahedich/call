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
    voice_presets,
    recommendations,
    agent_management,
    knowledge,
)
from routers.ws_transcript import router as ws_transcript_router
from middleware.auth import AuthMiddleware
from config.settings import settings
from services.tts.factory import get_tts_orchestrator, shutdown_tts
from services.telemetry.worker import TelemetryWorker
from services.telemetry import telemetry_queue
from services.cache_strategy import CacheStrategy, create_cache_strategy
from services.preset_samples import PresetSampleService
from database.session import AsyncSessionLocal

# Cache strategy for preset sample caching (Story 2.6)
_cache_strategy: CacheStrategy | None = None


def get_cache_strategy() -> CacheStrategy | None:
    """Get the cache strategy instance."""
    global _cache_strategy
    return _cache_strategy


async def get_preset_sample_service() -> PresetSampleService | None:
    """Get or create the PresetSampleService instance using dependency injection.

    This function can be used with FastAPI Depends() for explicit dependency injection.
    Returns None if cache strategy is not available.
    """
    cache_strategy = get_cache_strategy()
    if not cache_strategy:
        return None

    tts_orchestrator = get_tts_orchestrator()
    return PresetSampleService(cache_strategy, tts_orchestrator)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cache_strategy

    # Startup
    orchestrator = get_tts_orchestrator()
    await orchestrator.start_cleanup_task()

    # Initialize cache strategy for preset sample caching (Story 2.6)
    redis_url = getattr(settings, "REDIS_URL", None)
    _cache_strategy = await create_cache_strategy(redis_url)

    if isinstance(_cache_strategy, type(None)):
        print(
            "Cache strategy not available (NoOpCache). Preset sample caching disabled."
        )
    else:
        cache_type = _cache_strategy.__class__.__name__
        print(f"Cache strategy initialized: {cache_type}")

    # Start telemetry worker (Story 2.4)
    if settings.TELEMETRY_WORKER_ENABLED:
        telemetry_worker = TelemetryWorker(AsyncSessionLocal)
        await telemetry_queue.start_worker(telemetry_worker.process_batch)

    # Recover stale processing records from crashes (Story 3.1)
    from routers.knowledge import recover_stale_processing_records

    await recover_stale_processing_records()

    # Recover stale processing knowledge base records (Story 3.1)
    try:
        from routers.knowledge import recover_stale_processing_records

        await recover_stale_processing_records()
    except Exception as e:
        print(f"Warning: knowledge base recovery failed: {e}")

    yield

    # Shutdown
    await shutdown_tts()

    # Close cache strategy
    if _cache_strategy:
        await _cache_strategy.close()

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
app.include_router(voice_presets.router, prefix="/api/v1", tags=["Voice Presets"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(agent_management.router, prefix="/api/v1", tags=["Agent Management"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["Knowledge Base"])
