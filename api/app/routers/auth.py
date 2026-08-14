import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import SESSION_COOKIE_NAME, get_current_context
from app.auth.oidc import OIDCClient, OIDCError
from app.auth.session import issue_session_token
from app.config import get_settings
from app.db.deps import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.services import audit
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/auth", tags=["auth"])
_STATE_COOKIE = "zionhq_oidc_state"


def get_oidc_client() -> OIDCClient:
    return OIDCClient()


def _redirect_uri(request: Request) -> str:
    """The browser's own origin, not this API process's -- Vite's dev
    proxy forwards it via X-Forwarded-Host/-Proto (web/vite.config.ts's
    xfwd: true) since this request actually arrives from the proxy on
    localhost, not from the browser directly. Falls back to
    oidc_redirect_fallback_host for non-proxied deployments (a single
    fixed public hostname, where this header simply won't be present).

    Must return the SAME value on both /auth/login and /auth/callback for
    a given browser session -- it does, because both read it off the same
    browser-forwarded origin, and by the time /auth/callback runs the
    browser is (by definition) already on that origin.
    """
    host = request.headers.get("x-forwarded-host") or request.headers.get(
        "host", get_settings().oidc_redirect_fallback_host
    )
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}/auth/callback"


@router.get("/login")
async def login(
    request: Request, response: Response, oidc: OIDCClient = Depends(get_oidc_client)
):
    state = secrets.token_urlsafe(24)
    url = oidc.authorization_url(state, _redirect_uri(request))
    response.set_cookie(_STATE_COOKIE, state, httponly=True, samesite="lax", max_age=600)
    return {"authorization_url": url}


@router.post("/callback")
async def callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    oidc: OIDCClient = Depends(get_oidc_client),
):
    expected_state = request.cookies.get(_STATE_COOKIE)
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid oidc state")

    try:
        tokens = await oidc.exchange_code(code, _redirect_uri(request))
        identity = await oidc.verify_id_token(tokens["id_token"], tokens["access_token"])
    except OIDCError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = (
        await db.execute(select(User).where(User.auth_subject_id == identity.subject))
    ).scalar_one_or_none()

    if user is None:
        # First login for this identity: match a pre-invited, not-yet-linked
        # user record by email. Phase 1 simplification for a single shared
        # deployment -- see IMPLEMENTATION_PLAN §1.2/ARCHITECTURE §6.
        user = (
            await db.execute(
                select(User).where(User.email == identity.email, User.auth_subject_id.is_(None))
            )
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "no invited user found for this email")
        user.auth_subject_id = identity.subject

    session_token = issue_session_token(user.id, user.tenant_id, user.role.value)
    ctx = TenantContext(tenant_id=user.tenant_id, user_id=user.id, role=user.role.value)
    await audit.record(db, ctx, "auth.login")
    await db.commit()

    settings = get_settings()
    response.delete_cookie(_STATE_COOKIE)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        httponly=True,
        samesite="lax",
        secure=settings.env != "dev",
        max_age=settings.session_ttl_seconds,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response, ctx: TenantContext = Depends(get_current_context)):
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_current_context),
):
    user = (await db.execute(select(User).where(User.id == ctx.user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session user no longer exists")
    return UserOut.model_validate(user)
