import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Cold Caller API"
    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = "https://api.clerk.dev/v1/jwks"
    CLERK_WEBHOOK_SECRET: str = ""

    VAPI_WEBHOOK_SECRET: str = ""
    VAPI_API_KEY: str = ""
    VAPI_BASE_URL: str = "https://api.vapi.ai"

    BRANDING_CNAME_TARGET: str = "cname.call.app"

    DEFAULT_MONTHLY_CALL_CAP: int = 1000
    PLAN_CALL_CAPS: dict[str, int] = {"free": 1000, "pro": 25000, "enterprise": 100000}

    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_BASE_URL: str = "https://api.elevenlabs.io/v1"
    CARTESIA_API_KEY: str = ""
    CARTESIA_BASE_URL: str = "https://api.cartesia.ai"
    TTS_PRIMARY_PROVIDER: str = "elevenlabs"
    TTS_FALLBACK_PROVIDER: str = "cartesia"
    TTS_LATENCY_THRESHOLD_MS: int = 500
    TTS_CONSECUTIVE_SLOW_THRESHOLD: int = 3
    TTS_AUTO_RECOVERY_ENABLED: bool = True
    TTS_RECOVERY_HEALTHY_COUNT: int = 5
    TTS_RECOVERY_LATENCY_MS: int = 300
    TTS_RECOVERY_COOLDOWN_SEC: int = 60
    TTS_SESSION_TTL_SEC: int = 3600
    TTS_CIRCUIT_OPEN_SEC: int = 30

    PRESET_SAMPLE_TEXTS: dict[str, str] = {
        "sales": "Hi, this is Alex from TechCorp. I'm calling to show you how our platform can increase your sales by 30% in just 30 days.",
        "support": "Thank you for calling TechCorp support. I'm here to help you resolve any issues you're experiencing.",
        "marketing": "Hey there! I'm excited to tell you about our amazing new product that's changing the industry.",
    }
    SAMPLE_CACHE_TTL_SECONDS: int = 86400
    REDIS_URL: str = "redis://localhost:6379/0"

    TELEMETRY_QUEUE_MAX_SIZE: int = 10000
    TELEMETRY_BATCH_SIZE: int = 100
    TELEMETRY_PUSH_TIMEOUT_MS: int = 2
    TELEMETRY_WORKER_ENABLED: bool = True

    AI_PROVIDER: str = "openai"
    AI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_EMBEDDING_DIMENSIONS: int = 1536
    AI_LLM_MODEL: str = "gpt-4o-mini"
    AI_LLM_TEMPERATURE: float = 0.7
    AI_LLM_MAX_TOKENS: int = 2048
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    RAG_SIMILARITY_THRESHOLD: float = 0.7
    NAMESPACE_GUARD_ENABLED: bool = True
    NAMESPACE_AUDIT_MAX_PAIRS: int = 100

    @field_validator("RAG_SIMILARITY_THRESHOLD")
    @classmethod
    def validate_similarity_threshold(cls, v: float) -> float:
        clamped = max(0.0, min(1.0, v))
        if clamped != v:
            _logger.warning(
                "RAG_SIMILARITY_THRESHOLD clamped from %s to %s", v, clamped
            )
        return clamped

    @field_validator("NAMESPACE_AUDIT_MAX_PAIRS")
    @classmethod
    def validate_audit_max_pairs(cls, v: int) -> int:
        if v < 1:
            raise ValueError("NAMESPACE_AUDIT_MAX_PAIRS must be >= 1")
        return v

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError(
                'REDIS_URL must start with "redis://" or "rediss://" for TLS. '
                "Example: redis://localhost:6379/0 or rediss://your-redis-server:6380/0"
            )
        return v

    @model_validator(mode="after")
    def auto_set_ai_provider_defaults(self) -> "Settings":
        if self.AI_PROVIDER == "gemini":
            if self.AI_EMBEDDING_MODEL == "text-embedding-3-small":
                self.AI_EMBEDDING_MODEL = "gemini-embedding-001"
            if self.AI_EMBEDDING_DIMENSIONS == 1536:
                self.AI_EMBEDDING_DIMENSIONS = 3072
            if self.AI_LLM_MODEL == "gpt-4o-mini":
                self.AI_LLM_MODEL = "gemini-2.0-flash"
        return self


settings = Settings()
