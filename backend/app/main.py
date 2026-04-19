import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routes import auth, boards, ai

logger = logging.getLogger(__name__)

app = FastAPI(title="Project Management MVP")

# CORS — primarily for local frontend dev server (localhost:3000)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline';"
    )
    return response


app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(ai.router)

static_dir = Path(os.getenv("STATIC_DIR", str(Path(__file__).parent.parent / "static")))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/test")
def test_api():
    return {"message": "Hello from FastAPI!", "value": 42}


if (static_dir / "_next").exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="_next")

if (static_dir / "public").exists():
    app.mount("/public", StaticFiles(directory=static_dir / "public"), name="public")


@app.on_event("startup")
def startup() -> None:
    if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        logger.warning("No AI API key set — AI features will fail at runtime")
    init_db()


def _safe_file_path(base: Path, rel: str) -> Path | None:
    """Resolve rel under base and return None if it escapes base."""
    try:
        resolved = (base / rel).resolve()
        if str(resolved).startswith(str(base.resolve())):
            return resolved
    except Exception:
        pass
    return None


def is_authenticated(request: Request) -> bool:
    return auth.is_request_authenticated(request)


@app.get("/{full_path:path}")
def serve_spa(full_path: str, request: Request):
    protected_routes = ["/app", "/board", "/dashboard"]
    if any(full_path.startswith(route) for route in protected_routes):
        if not is_authenticated(request):
            login_path = static_dir / "index.html"
            if login_path.exists():
                return FileResponse(login_path)

    file_path = _safe_file_path(static_dir, full_path)
    if file_path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    html_path = _safe_file_path(static_dir, f"{full_path}.html")
    if html_path and html_path.exists():
        return FileResponse(html_path)

    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {"error": "Not found"}


@app.get("/")
def serve_root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not yet built"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
