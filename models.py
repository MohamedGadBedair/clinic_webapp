from database import Base
from uuid import UUID

from datetime import datetime, date as PyDate, time as PyTime, timezone

from sqlalchemy import DATE, DateTime, Time, ForeignKey, String, Text, Boolean, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
# =========================={User Table}============================
# User Table
class User(Base):
    __tablename__ = "users"
    username:Mapped[str]=mapped_column(unique=True,nullable=False)
    email:Mapped[str]=mapped_column(unique=True,nullable=False)
    role:Mapped[str]=mapped_column(String(20),nullable=False) 
    phone_code: Mapped[str|None] = mapped_column(String(8), default="+20",nullable=True)
    phone: Mapped[str|None] = mapped_column(String(20), default="",nullable=True)
    dob: Mapped[PyDate | None] = mapped_column(DATE, nullable=True)
    city: Mapped[str|None] = mapped_column(String(40), default="", nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str|None] = mapped_column(Text, default="", nullable=True)

    user_profile_img:Mapped[str|None]=mapped_column(nullable=True,default=None)
    
    password_hash:Mapped[str|None]=mapped_column(String(200),nullable=True)
    validated:Mapped[bool]=mapped_column(default=False)
    

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime, default=utcnow,onupdate=utcnow)
    
    reset_tokens:Mapped[list['PasswordResetToken']]=relationship(
        back_populates='user',
        cascade='all, delete-orphan'
    )
    validate_Email_token:Mapped[list['ValidateEmailToken']]=relationship(
        back_populates='user',
        cascade='all, delete-orphan'
    )

    @property
    def image_path(self):
        if self.user_profile_img:
            return f'/media/profile_pics/{self.user_profile_img}'
        return '/static/profile_pics/default.jpg'

class DoctorClient(Base):
    __tablename__ = "doctors_clients"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, primary_key=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, primary_key=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)
# ======================{Temp Tokens Tables}=================================================
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime,nullable=False)
    user: Mapped[User] = relationship(back_populates="reset_tokens")
class ValidateEmailToken(Base):
    __tablename__ = "validate_email_token"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime,nullable=False)
    user: Mapped[User] = relationship(back_populates="validate_Email_token")

# ======================{Booking Table}=================================================
class BookingType(Base):
    __tablename__ = "booking_types"
    __table_args__ = (UniqueConstraint("doctor_id", "title", name="uq_type_title_per_doctor"),)

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(40))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    description: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
# ====================={Appointment Table}=================================================
class Appointment(Base):
    __tablename__ = "appointments"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type_id: Mapped[UUID | None] = mapped_column(ForeignKey("booking_types.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[PyDate] = mapped_column(DATE, index=True)
    time: Mapped[PyTime] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20), default="waiting")  # confirmed | waiting | completed | cancelled
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    type: Mapped[BookingType | None] = relationship()

# ====================={Conversation Table}=================================================
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("doctor_id", "client_id", name="uq_conversation"),)

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    unread: Mapped[int] = mapped_column(Integer, default=0)          # unread by the doctor
    client_unread: Mapped[int] = mapped_column(Integer, default=0)  # unread by the client

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan",
                                                     order_by="Message.id")

# ===================={Message Table}=================================================
class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender: Mapped[str] = mapped_column(String(10), default='sent')  # client | doctor
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

# ===================={Medical Files Table}=================================================
class MedicalFile(Base):
    __tablename__ = "medical_files"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(10),nullable=False)  # lab | imaging | report
    uploaded_by: Mapped[str] = mapped_column(String(10), default="doctor")  # doctor | client
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

