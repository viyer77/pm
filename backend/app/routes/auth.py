from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

VALID_USERNAME = "user"
VALID_PASSWORD = "password"

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str


def is_request_authenticated(request: Request) -> bool:
    session_cookie = request.cookies.get("session")
    return session_cookie == "authenticated"


def require_authenticated(request: Request) -> None:
    if not is_request_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    if request.username == VALID_USERNAME and request.password == VALID_PASSWORD:
        # Set secure HTTP-only cookie with session token
        response.set_cookie(
            key="session",
            value="authenticated",
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400  # 24 hours
        )
        return LoginResponse(success=True, message="Login successful")
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout", response_model=LoginResponse)
async def logout(response: Response):
    response.delete_cookie("session")
    return LoginResponse(success=True, message="Logout successful")

@router.get("/check")
async def check_auth(request: Request):
    if is_request_authenticated(request):
        return {"authenticated": True}
    return {"authenticated": False}
