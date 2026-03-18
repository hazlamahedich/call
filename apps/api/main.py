from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health


app = FastAPI(title="AI Cold Caller API", version="0.1.0")


# CORS and Routers
app.include_router(health.router, tags=["Health"])

