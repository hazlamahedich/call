from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Telemetry Queue Settings (Story 2.4)
    TELEMETRY_QUEUE_MAX_SIZE: int = 10000
    TELEMETRY_BATCH_SIZE: int = 100
    TELEMETRY_PUSH_TIMEOUT_MS: int = 2
    TELEMETRY_WORKER_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
