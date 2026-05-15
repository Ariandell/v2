"""
Luna Music AI — Application entry point.

Creates the FastAPI app, loads models at startup,
and registers all route modules.
"""

import sys
import os
import warnings
from pathlib import Path
from contextlib import asynccontextmanager

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emoji
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore")

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.database import engine, Base
from src.api.services.ai_models import ModelRegistry
from src.api.routes import health, analysis, search, stream, history, playlists


# ── Model Registry (singleton) ───────────────────────────────────────────────

registry = ModelRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + load AI models.  Shutdown: cleanup."""
    # Database
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized.")
    except Exception as e:
        print(f"Warning: Could not initialize DB: {e}")

    # AI Models
    registry.load()

    # Inject registry into analysis router
    analysis.init(registry)

    yield
    print("Shutting down AI Music Server...")


# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(title="Luna Music AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to actual frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(search.router)
app.include_router(stream.router)
app.include_router(history.router)
app.include_router(playlists.router)


# ── CLI Entry ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
