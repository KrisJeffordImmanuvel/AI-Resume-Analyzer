"""FastAPI entry point. Run from the backend folder with: uvicorn main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import check_db, init_db, make_engine, make_session_factory

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = make_engine(settings.database_url)
    init_db(engine)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="AI Resume & Career Intelligence Platform", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(request: Request) -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "ai_configured": settings.has_api_key,
        "demo_mode": settings.demo_mode,
        "ai_mode": "live" if settings.ai_enabled else "fallback",
        "fallback_reason": settings.fallback_reason,
        "database": "ok" if check_db(request.app.state.engine) else "error",
    }
