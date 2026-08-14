from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserInvite, UserOut
from app.services import audit
from app.services.tenant_repo import TenantContext, TenantRepo

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    users = (await db.execute(repo.scoped(User).order_by(User.email))).scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post("/invite", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: UserInvite,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    user = repo.stamp_tenant(User(email=body.email, role=body.role))
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "user already exists for this tenant"
        ) from exc

    await audit.record(
        db, ctx, "user.invite", payload={"email": body.email, "role": body.role.value}
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)
