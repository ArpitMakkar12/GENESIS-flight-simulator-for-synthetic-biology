from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import simulate, constructs, parts, knowledge, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: load ML models, verify DB connection
    print("BioSandbox API starting up...")
    yield
    # Shutdown: cleanup resources
    print("BioSandbox API shutting down...")


app = FastAPI(
    title="BioSandbox API",
    description="AI-powered E. coli simulation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(simulate.router, prefix="/api/v1", tags=["Simulation"])
app.include_router(constructs.router, prefix="/api/v1", tags=["Constructs"])
app.include_router(parts.router, prefix="/api/v1", tags=["Parts"])
app.include_router(knowledge.router, prefix="/api/v1", tags=["Knowledge"])
app.include_router(results.router, prefix="/api/v1", tags=["Results"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "biosandbox-api"}
