"""One password for the whole app, for when it is published as a website.

Off unless APP_PASSWORD is set, so running on your own PC works exactly as before.
When it is set, every /api/ address (and the /docs pages) needs a signed-in browser.
Signing in gives the browser a session cookie signed with HMAC-SHA256; the server
keeps no session list. Changing APP_PASSWORD or SESSION_SECRET signs everyone out.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from config import Settings, get_settings

logger = logging.getLogger("resume_analyzer")

COOKIE_NAME = "truescope_session"
SESSION_SECONDS = 30 * 24 * 60 * 60  # stay signed in for 30 days
MIN_PASSWORD_LENGTH = 12

# Without SESSION_SECRET, sessions are signed with a key made at startup (so a restart signs you out).
_PROCESS_SECRET = secrets.token_hex(32)

# Addresses that need sign-in besides /api/ (the interactive API pages show every endpoint).
_PROTECTED_PAGES = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def _signing_key(settings: Settings) -> bytes:
    secret = settings.session_secret or _PROCESS_SECRET
    return hashlib.sha256(f"{secret}\0{settings.app_password}".encode()).digest()


def make_token(settings: Settings, now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + SESSION_SECONDS)
    signature = hmac.new(_signing_key(settings), str(expires).encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def token_valid(token: str | None, settings: Settings, now: float | None = None) -> bool:
    if not token or "." not in token:
        return False
    expires, _, signature = token.partition(".")
    if not expires.isdigit():
        return False
    expected = hmac.new(_signing_key(settings), expires.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected) and int(expires) > (time.time() if now is None else now)


def password_matches(given: str, settings: Settings) -> bool:
    # Compare fixed-length digests, so the time taken says nothing about the password.
    a = hashlib.sha256(given.encode()).digest()
    b = hashlib.sha256(settings.app_password.encode()).digest()
    return hmac.compare_digest(a, b)


def check_password_settings(settings: Settings) -> None:
    """Called at startup. With REQUIRE_PASSWORD on (the website), refuse to run unprotected or without a database."""
    if settings.require_password and len(settings.app_password) < MIN_PASSWORD_LENGTH:
        raise RuntimeError(
            f"REQUIRE_PASSWORD is on, so APP_PASSWORD must be set to at least {MIN_PASSWORD_LENGTH} "
            "characters. The app will not start without it (see README, Publish on Render)."
        )
    if settings.require_password and not os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError(
            "REQUIRE_PASSWORD is on, so DATABASE_URL must be set (your Neon database address). Without it "
            "the website would keep data in a file that is lost at every restart (see README, Publish on Render)."
        )
    if settings.password_required and not settings.session_secret:
        logger.warning("APP_PASSWORD is set but SESSION_SECRET is not: every restart signs you out.")


class LoginLimiter:
    """Slows down password guessing: a few wrong tries per address, and a cap for everyone together."""

    def __init__(self, per_client: int = 5, overall: int = 20, window: float = 15 * 60, clock=time.monotonic):
        self.per_client = per_client
        self.overall = overall
        self.window = window
        self.clock = clock
        self._by_client: dict[str, deque] = defaultdict(deque)
        self._all: deque = deque()
        self._lock = threading.Lock()

    def _trim(self, times: deque, now: float) -> None:
        while times and times[0] <= now - self.window:
            times.popleft()

    def retry_after(self, client: str) -> int:
        """Seconds to wait before trying again, or 0 when a try is allowed now."""
        with self._lock:
            now = self.clock()
            mine = self._by_client[client]
            self._trim(mine, now)
            self._trim(self._all, now)
            waits = []
            if len(mine) >= self.per_client:
                waits.append(mine[0] + self.window - now)
            if len(self._all) >= self.overall:
                waits.append(self._all[0] + self.window - now)
            return max(1, int(max(waits)) + 1) if waits else 0

    def failed(self, client: str) -> None:
        with self._lock:
            now = self.clock()
            self._by_client[client].append(now)
            self._all.append(now)

    def succeeded(self, client: str) -> None:
        with self._lock:
            self._by_client.pop(client, None)


limiter = LoginLimiter()


# ---- API ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["sign in"])


class AuthStatus(BaseModel):
    required: bool  # true when the app is protected by a password
    signed_in: bool


class LoginRequest(BaseModel):
    password: str


def _status(request: Request, settings: Settings) -> AuthStatus:
    if not settings.password_required:
        return AuthStatus(required=False, signed_in=True)
    return AuthStatus(required=True, signed_in=token_valid(request.cookies.get(COOKIE_NAME), settings))


@router.get("/status", response_model=AuthStatus)
def status(request: Request) -> AuthStatus:
    return _status(request, get_settings())


@router.post("/login", response_model=AuthStatus)
def login(body: LoginRequest, request: Request, response: Response) -> AuthStatus:
    settings = get_settings()
    if not settings.password_required:
        return AuthStatus(required=False, signed_in=True)
    client = request.client.host if request.client else "unknown"
    wait = limiter.retry_after(client)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            429,
            f"Too many wrong passwords. Please wait about {minutes} minute{'s' if minutes != 1 else ''} and try again.",
            headers={"Retry-After": str(wait)},
        )
    if not password_matches(body.password, settings):
        limiter.failed(client)
        raise HTTPException(401, "That password is not right.")
    limiter.succeeded(client)
    response.set_cookie(
        COOKIE_NAME,
        make_token(settings),
        max_age=SESSION_SECONDS,
        httponly=True,  # page scripts cannot read it
        samesite="lax",  # other websites cannot send requests with it
        secure=request.url.scheme == "https",
        path="/",
    )
    return AuthStatus(required=True, signed_in=True)


@router.post("/logout", response_model=AuthStatus)
def logout(request: Request, response: Response) -> AuthStatus:
    settings = get_settings()
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/")
    return AuthStatus(required=settings.password_required, signed_in=not settings.password_required)


# ---- Middleware ----------------------------------------------------------------------


def _needs_sign_in(path: str) -> bool:
    if path in _PROTECTED_PAGES:
        return True
    return path.startswith("/api/") and not path.startswith("/api/auth/")


def _cookie(scope, name: str) -> str | None:
    for key, value in scope.get("headers", []):
        if key == b"cookie":
            for part in value.decode("latin-1").split(";"):
                k, _, v = part.strip().partition("=")
                if k == name:
                    return v
    return None


class RequireSignIn:
    """ASGI middleware: with APP_PASSWORD set, protected addresses answer 401 until you sign in.

    The web page itself (HTML, scripts, icons) stays public: it holds no data and shows the sign-in form.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("method") != "OPTIONS" and _needs_sign_in(scope["path"]):
            settings = get_settings()
            if settings.password_required and not token_valid(_cookie(scope, COOKIE_NAME), settings):
                body = json.dumps({"detail": "Please sign in first."}).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (b"cache-control", b"no-store"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


class SecurityHeaders:
    """ASGI middleware: standard browser protections on every response."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        https = scope.get("scheme") == "https"

        async def add_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                extra = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"same-origin"),
                ]
                if https:
                    extra.append((b"strict-transport-security", b"max-age=31536000"))
                headers += [(k, v) for k, v in extra if k not in present]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, add_headers)
