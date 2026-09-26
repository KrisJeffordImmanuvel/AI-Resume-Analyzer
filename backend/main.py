"""FastAPI entry point.

Everyday use: run start.ps1 from the project folder; it builds the frontend if
needed and serves the whole app at http://localhost:8000.
Development: run "uvicorn main:app --reload" from the backend folder and
"npm run dev" in the frontend folder (http://localhost:5173).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from config import get_settings
from database import check_db, init_db, make_engine, make_session_factory
from parsing import MAX_UPLOAD_BYTES
from request_limit import RequestSizeLimit
from routers import analyses, coaching, data, evidence, jobs, resume_tools, samples
from routers.jobs import MAX_FILES_PER_UPLOAD
from schemas import HealthResponse

APP_VERSION = "1.0.0"
logger = logging.getLogger("resume_analyzer")


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


app = FastAPI(title="Truescope", version=APP_VERSION, lifespan=lifespan)

# 10 resumes of up to 5 MB in one Job Provider upload, plus room for the form itself.
MAX_REQUEST_BYTES = MAX_FILES_PER_UPLOAD * MAX_UPLOAD_BYTES + 1024 * 1024
app.add_middleware(RequestSizeLimit, max_bytes=MAX_REQUEST_BYTES)  # added first, so CORS wraps its replies
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Any unhandled error: log the details for the developer, send the user a plain message."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on the server. The details were written to the app's "
            "PowerShell window. Please try again; if it keeps happening, close that window "
            "and run start.ps1 again."
        },
    )


app.include_router(analyses.router)
app.include_router(coaching.router)
app.include_router(resume_tools.router)
app.include_router(evidence.router)
app.include_router(jobs.router)
app.include_router(samples.router)
app.include_router(data.router)


@app.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        ai_configured=settings.has_api_key,
        demo_mode=settings.demo_mode,
        ai_mode="live" if settings.ai_enabled else "fallback",
        fallback_reason=settings.fallback_reason,
        database="ok" if check_db(request.app.state.engine) else "error",
        ai_model=settings.gemini_model if settings.ai_enabled else None,
        semantic_matching="enabled" if settings.semantic_matching else "disabled",
        ai_timeout_seconds=settings.ai_timeout_seconds,
    )


# ---- The built frontend (must stay the last route) -----------------------------

_NOT_BUILT = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Not built yet</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;line-height:1.5}
code{background:#eee;padding:.1rem .3rem;border-radius:4px}</style></head><body>
<h1>The app's web page has not been built yet</h1>
<p>The server is running, but the web page has not been built. In PowerShell, from the project folder, run:</p>
<p><code>.\\start.ps1</code></p>
<p>That builds the page and starts everything at this address. (Developers using
<code>npm run dev</code> should open <a href="http://localhost:5173">http://localhost:5173</a> instead.)</p>
</body></html>"""


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str):
    """Serve the built frontend; unknown paths get index.html so the app can handle them."""
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "Not found.")
    dist = Path(get_settings().frontend_dist).resolve()
    index = dist / "index.html"
    if not index.is_file():
        return HTMLResponse(_NOT_BUILT, status_code=503)
    if path:
        candidate = (dist / path).resolve()
        # Only files inside the build folder, never "../" tricks.
        if candidate.is_file() and dist in candidate.parents:
            # Built assets have content hashes in their names, so they can be cached for long.
            cache = "public, max-age=31536000, immutable" if candidate.parent.name == "assets" else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
