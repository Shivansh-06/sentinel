from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, verify_password
from app.config import settings
from app.database import get_db
from app.models.login_audit import LoginAudit

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: dict


def request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def record_login(
    db: AsyncSession,
    request: Request,
    username: str,
    success: bool,
    failure_reason: str | None = None,
) -> None:
    db.add(
        LoginAudit(
            username=username,
            success=success,
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
            failure_reason=failure_reason,
        )
    )
    await db.commit()


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    username = payload.username.strip()

    if username != settings.auth_username or not verify_password(payload.password):
        await record_login(db, request, username or "<blank>", False, "invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_at = create_access_token(username)
    await record_login(db, request, username, True)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "user": {"username": username},
    }


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}


@router.get("/auth/login-events")
async def login_events(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LoginAudit).order_by(LoginAudit.created_at.desc()).limit(100)
    )
    events = result.scalars().all()
    return {
        "events": [
            {
                "id": event.id,
                "username": event.username,
                "success": event.success,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "failure_reason": event.failure_reason,
                "created_at": event.created_at,
            }
            for event in events
        ]
    }
