from database import Base
from uuid import UUID

from datetime import datetime, date as PyDate, time as PyTime, timezone

from sqlalchemy import DATE, DateTime, Time, ForeignKey, String, Text, Boolean, Numeric, Integer, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
# ==================================={User Table}======================================
# User Table
class User(Base):
    __tablename__ = "users"
    username:Mapped[str]=mapped_column(unique=True,nullable=False)
    email:Mapped[str]=mapped_column(unique=True,nullable=False,index=True)
    role:Mapped[str]=mapped_column(String(20),nullable=False) 
    phone_code: Mapped[str|None] = mapped_column(String(8), default="+20",nullable=True)
    phone: Mapped[str|None] = mapped_column(String(20), default="",nullable=True)
    dob: Mapped[PyDate | None] = mapped_column(DATE, nullable=True)
    city: Mapped[str|None] = mapped_column(String(40), default="", nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str|None] = mapped_column(Text, default="", nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=True,server_default="true")
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
    @property
    def user_age(self) -> int | None:
        if not self.dob:
            return None
        today = datetime.now().date()
        # Calculate years, accounting for whether their birthday has occurred yet this year
        return (
            today.year
            - self.dob.year
            - ((today.month, today.day) < (self.dob.month, self.dob.day))
        )
    
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
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime, default=utcnow,onupdate=utcnow)
# ====================={Appointment Table}=================================================
class Appointment(Base):
    __tablename__ = "appointments"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type_id: Mapped[UUID | None] = mapped_column(ForeignKey("booking_types.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[PyDate] = mapped_column(DATE, index=True,primary_key=True)
    time: Mapped[PyTime] = mapped_column(Time,primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # confirmed | waiting | completed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime, default=utcnow,onupdate=utcnow)
    
    type: Mapped[BookingType | None] = relationship(lazy="selectin")
    client: Mapped[User] = relationship(lazy="selectin", primaryjoin="User.id==Appointment.client_id", viewonly=True)
    
    @property
    def appointment_type(self):
        if self.type_id:
            return self.type.title
    @property
    def appointment_price(self):
        if self.type_id:
            return self.type.price
    @property
    def client_name(self):
        return f'{self.client.username}' 
# ==================={Payment Table}=================================================
class Payment(Base):
    __tablename__ = "payments"

    appointment_id:Mapped[UUID] = mapped_column(ForeignKey("appointments.id"), index=True,unique=True)
    doctor_email: Mapped[UUID] = mapped_column(String, index=True)
    client_email: Mapped[UUID] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # pending | completed | failed
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)      
    updated_at:Mapped[datetime]=mapped_column(DateTime, default=utcnow,onupdate=utcnow)
# ====================={Conversation Table}=================================================
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("doctor_id", "client_id", name="uq_conversation"),)

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    doctor_unread: Mapped[int] = mapped_column(Integer, default=0)  # unread by the doctor
    client_unread: Mapped[int] = mapped_column(Integer, default=0)  # unread by the client
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)      

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan",
                                                     order_by="Message.id")
# ===================={Message Table}=================================================
class Message(Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[UUID] = mapped_column(index=True)  
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages",lazy="selectin")
# # ==================={unsentedmail Table}=================================================
class UnsentEmail(Base):
    __tablename__ = "unsent_emails"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(String(20), nullable=False)  
    data: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    user: Mapped[User] = relationship(lazy="selectin", primaryjoin="User.id==UnsentEmail.user_id", viewonly=True)    
# # =================={Notification Table}=================================================
# class Notification(Base):
#     __tablename__ = "notifications"

#     user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
#     message: Mapped[str] = mapped_column(String(255))
#     read: Mapped[bool] = mapped_column(Boolean, default=False)
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
# # ==================={Feedback Table}=================================================
# class Feedback(Base):
#     __tablename__ = "feedbacks"

#     appointment_id: Mapped[UUID] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)
#     user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
#     rating: Mapped[int] = mapped_column(Integer, default=5)  # 1 to 5
#     comment: Mapped[str] = mapped_column(Text, default="")
#     created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
# ===================={blook Table}=================================================
class BlockedEmail(Base):
    """Emails the doctor has blocked. Kept independently of the Patient row on purpose."""
    __tablename__ = "blocked_emails"
    __table_args__ = (UniqueConstraint("doctor_id", "email", name="uq_blocked_email"),)

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(255),index=True, nullable=False) # as entered, shown to the doctor
    name: Mapped[str] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

# ===================={Medical Files Table}=================================================
class MedicalFile(Base):
    __tablename__ = "medical_files"

    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(10),nullable=False)  # lab | imaging | report
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    @property
    def file_path(self):
        return f'/uploads/{self.filename}'
