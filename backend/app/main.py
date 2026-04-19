from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .routes import auth

app = FastAPI(title="Project Management MVP")

# Include auth routes
app.include_router(auth.router)

# Static directory path
static_dir = Path(__file__).parent.parent / "static"

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}

# Test API endpoint
@app.get("/api/test")
def test_api():
    return {"message": "Hello from FastAPI!", "value": 42}

# Mount _next directory for static Next.js assets
if (static_dir / "_next").exists():
    app.mount("/_next", StaticFiles(directory=static_dir / "_next"), name="_next")

# Mount public assets
if (static_dir / "public").exists():
    app.mount("/public", StaticFiles(directory=static_dir / "public"), name="public")

def is_authenticated(request: Request) -> bool:
    """Check if request has valid session cookie"""
    session_cookie = request.cookies.get("session")
    return session_cookie == "authenticated"

# Catch-all route handler for Next.js SPA routing
@app.get("/{full_path:path}")
def serve_spa(full_path: str, request: Request):
    # Check if authenticated for protected routes
    protected_routes = ["/app", "/board", "/dashboard"]
    if any(full_path.startswith(route) for route in protected_routes):
        if not is_authenticated(request):
            # Redirect to login by serving login page
            login_path = static_dir / "index.html"
            if login_path.exists():
                return FileResponse(login_path)
    
    # Try to serve the exact file first
    file_path = static_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Try to serve as HTML (for Next.js routes)
    html_path = static_dir / f"{full_path}.html"
    if html_path.exists():
        return FileResponse(html_path)
    
    # Fall back to index.html for SPA routing
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return {"error": "Not found"}

# Root path handler
@app.get("/")
def serve_root(request: Request):
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not yet built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
