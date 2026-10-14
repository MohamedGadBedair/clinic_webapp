from database import Base
from uuid import UUID

from datetime import UTC, datetime, date as PyDate, time as PyTime, timezone
import enum

from sqlalchemy import DATE, DateTime, Time, ForeignKey, String, Text, Boolean, Numeric, Integer, UniqueConstraint,Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
# =========================={Enums}============================
class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"

class UserRole(enum.Enum):
    PATIENT = "patient"
    ASSESTANT = "assestant"
    DOCTOR = "doctor"
    ADMIN = "admin"

class AppointmentStatus(enum.Enum):
    CONFIRMED = "confirmed"
    WAITING = "waiting"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class MedicalFileType(enum.Enum):
    LAB = "lab"
    IMAGING = "imaging"
    REPORT = "report"
# =========================={User Table}============================
# User Table
class User(Base):
    __tablename__ = "users"
    username:Mapped[str]=mapped_column(unique=True,nullable=False)
    email:Mapped[str]=mapped_column(unique=True,nullable=False)
    phone_code: Mapped[str] = mapped_column(String(8), default="+20")
    phone: Mapped[str] = mapped_column(String(20), default="")
    dob: Mapped[PyDate | None] = mapped_column(DATE, nullable=True)
    city: Mapped[str] = mapped_column(String(80), default="")
    gender: Mapped[Gender | None] = mapped_column(SQLEnum(Gender), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")

    user_profile_img:Mapped[str|None]=mapped_column(nullable=True,default=None)
    
    password_hash:Mapped[str|None]=mapped_column(String(200),nullable=True)
    validated:Mapped[bool]=mapped_column(default=False)
    
    role:Mapped[UserRole]=mapped_column(SQLEnum(UserRole),default=UserRole.PATIENT)

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

class DoctorPatient(Base):
    __tablename__ = "doctors_users"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, primary_key=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True, primary_key=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)

    doctor: Mapped["User"] = relationship()
    patient: Mapped["User"] = relationship()
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
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type_id: Mapped[UUID | None] = mapped_column(ForeignKey("booking_types.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[PyDate] = mapped_column(DATE, index=True)
    time: Mapped[PyTime] = mapped_column(Time)
    status: Mapped[AppointmentStatus] = mapped_column(SQLEnum(AppointmentStatus), default= AppointmentStatus.WAITING)  # confirmed | waiting | completed | cancelled
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[User] = relationship()
    type: Mapped[BookingType | None] = relationship()

# ====================={Conversation Table}=================================================
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("doctor_id", "patient_id", name="uq_conversation"),)

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    unread: Mapped[int] = mapped_column(Integer, default=0)          # unread by the doctor
    patient_unread: Mapped[int] = mapped_column(Integer, default=0)  # unread by the patient

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan",
                                                     order_by="Message.id")

# ===================={Message Table}=================================================
class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender: Mapped[MessageStatus] = mapped_column(SQLEnum(MessageStatus), default=MessageStatus.SENT)  # patient | doctor
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

# ===================={Medical Files Table}=================================================
class MedicalFile(Base):
    __tablename__ = "medical_files"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[MedicalFileType] = mapped_column(SQLEnum(MedicalFileType),nullable=False)  # lab | imaging | report
    uploaded_by: Mapped[str] = mapped_column(String(10), default="doctor")  # doctor | patient
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    patient: Mapped[User] = relationship()
