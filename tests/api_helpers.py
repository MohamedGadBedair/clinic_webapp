from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_access_token, hash_password
from models import User


async def make_user(
    db: AsyncSession,
    *,
    role: str,
    username: str | None = None,
    email: str | None = None,
) -> User:
    """Persist an authenticated API user without relying on email delivery."""
    suffix = uuid4().hex[:10]
    user = User(
        username=username or f"{role.lower()}_{suffix}",
        email=email or f"{role.lower()}_{suffix}@example.com",
        role=role,
        password_hash=hash_password("password123"),
        validated=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}
