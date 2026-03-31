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

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
