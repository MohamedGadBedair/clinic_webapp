from database import Base

from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

# User Table
class User(Base):
    __tablename__='users'

    id:Mapped[int]=mapped_column(primary_key=True,index=True)
    username:Mapped[str]=mapped_column(unique=True,nullable=False)
    email:Mapped[str]=mapped_column(unique=True,nullable=False)
    password_hash:Mapped[str|None]=mapped_column(String(200),nullable=True)

    image_file:Mapped[str|None]=mapped_column(nullable=True,default=None)

    created_at:Mapped[datetime]=mapped_column(default=datetime.now(UTC))
    updated_at:Mapped[datetime]=mapped_column(default=datetime.now(UTC),onupdate=datetime.now(UTC))
    
    reset_tokens:Mapped[list['PasswordResetToken']]=relationship(
        back_populates='user',
        cascade='all, delete-orphan'
    )

    @property
    def image_path(self):
        if self.image_file:
            return f'/media/profile_pics/{self.image_file}'
        return '/static/profile_pics/default.jpg'

# PasswordResetToken table
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="reset_tokens")
