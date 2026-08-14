"""Seed a dev tenant + admin user so Phase 1's "log in as admin" acceptance
criterion has something to log in as. Not for production use -- there is no
tenant self-signup flow yet (ARCHITECTURE.md §6, single shared deployment
assumption).

Usage: python -m scripts.seed_dev --email you@example.com
"""

import argparse
import asyncio

from sqlalchemy import select

from app.db.base import get_session_factory
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User


async def seed(email: str, tenant_name: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        tenant_result = await session.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.flush()
            print(f"created tenant {tenant.name} ({tenant.id})")

        user_result = await session.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            user = User(tenant_id=tenant.id, email=email, role=UserRole.admin)
            session.add(user)
            print(f"created admin user {email}")
        else:
            user.role = UserRole.admin
            print(f"{email} already exists, ensured admin role")

        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--tenant", default="Dev Tenant")
    args = parser.parse_args()
    asyncio.run(seed(args.email, args.tenant))
