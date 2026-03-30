from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health, webhooks, branding, clients, onboarding, usage
from middleware.auth import AuthMiddleware
from config.settings import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
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
