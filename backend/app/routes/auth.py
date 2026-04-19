import logging
import os
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

VALID_USERNAME = os.getenv("APP_USERNAME", "user")
VALID_PASSWORD = os.getenv("APP_PASSWORD", "password")

# Secure token store: token -> expiry timestamp
_sessions: dict[str, float] = {}
SESSION_TTL = 3600  # 1 hour

# Simple sliding-window rate limiter for login: max 10 attempts per IP per minute
import collections as _collections
_login_attempts: dict[str, _collections.deque] = {}
_LOGIN_LIMIT = 10
_LOGIN_WINDOW = 60


def _is_login_rate_limited(ip: str) -> bool:
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = _collections.deque()
    window = _login_attempts[ip]
    while window and window[0] < now - _LOGIN_WINDOW:
        window.popleft()
    if len(window) >= _LOGIN_LIMIT:
        return True
    window.append(now)
    return False


def _prune_sessions() -> None:
    now = time.time()
    expired = [t for t, exp in list(_sessions.items()) if exp < now]
    for t in expired:
        del _sessions[t]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str


def is_request_authenticated(request: Request) -> bool:
    token = request.cookies.get("session")
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None or expiry < time.time():
        return False
    return True


def require_authenticated(request: Request) -> None:
    if not is_request_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    if _is_login_rate_limited(client_ip):
        logger.warning(f"Login rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many login attempts")

    if request.username == VALID_USERNAME and request.password == VALID_PASSWORD:
        _prune_sessions()
        token = secrets.token_urlsafe(32)
        _sessions[token] = time.time() + SESSION_TTL
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=False,  # set True in production (requires HTTPS)
            samesite="lax",
            max_age=SESSION_TTL,
        )
        logger.info(f"Login successful for user: {request.username}")
        return LoginResponse(success=True, message="Login successful")

    logger.warning(f"Login failed for user: {request.username} from IP: {client_ip}")
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/logout", response_model=LoginResponse)
async def logout(req: Request, response: Response):
    token = req.cookies.get("session")
    if token:
        _sessions.pop(token, None)
    response.delete_cookie("session")
    logger.info("Logout successful")
    return LoginResponse(success=True, message="Logout successful")


@router.get("/check")
async def check_auth(request: Request):
    if is_request_authenticated(request):
        return {"authenticated": True}
    return {"authenticated": False}
