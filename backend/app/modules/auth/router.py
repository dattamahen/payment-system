from fastapi import APIRouter, Depends
from app.modules.auth.schemas import LoginRequest, TokenResponse, RegisterRequest
from app.modules.auth.service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    return await AuthService.login(body.email, body.password)


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    return await AuthService.register(body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str):
    return await AuthService.refresh_token(refresh_token)
