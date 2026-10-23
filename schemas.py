from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime,date,time,timedelta
from uuid import UUID

from lists import(
    UserRole,
    Gender,
    MessageStatus,
    City,
    AppointmentStatus
)



#====================================={User Schemas}===================================
class UserBase(BaseModel):
    username:str = Field(min_length=2,max_length=50)
    email:EmailStr=Field(max_length=100)
class UserCreate(UserBase):
    role:UserRole
    doctor_id:UUID|None
    password:str = Field(min_length=8)
class UserUpdate(BaseModel):
    username: str|None = Field(default=None,min_length=2,max_length=50)
    email: EmailStr|None = Field(default=None,max_length=100)
    description: str|None = Field(default=None,max_length=255)
    phone_code:str|None=Field(default="+20",pattern=r"^\+\d{1,4}$", description="رمز الدولة بصيغة دولية")
    phone: str|None = Field(min_length=9, max_length=20, description="رقم الهاتف بصيغة دولية")
    dob: date|None = Field(default=None)
    city:City|None = Field(default=None)
    gender:Gender|None=None
class UserDelete(BaseModel):
    confirm:str='DELETE_MY_ACCOUNT'
    confirm_password:str
class UserPablic(BaseModel):
    id: UUID
    username:str 
    role:str|None=None
    city: str|None=None
    phone_code:str|None
    phone: str|None = None
    description: str|None = None
    gender:str|None=None
    user_profile_img: str|None
    image_path: str
    dob: date|None = None
    user_age: int|None = None
    is_online: bool
    model_config = ConfigDict(from_attributes=True)
class UserPrivate(UserPablic): 
    email:EmailStr
#===================================={Token Schemas}=====================================
class Token(BaseModel):
    access_token:str
    token_type:str
#================================={Reset Password Schemas}================================
class ForgotPasswordRequest(BaseModel):
    email:EmailStr=Field(max_length=120)
class ResetPasswordRequest(BaseModel):
    token:str
    new_password:str=Field(min_length=8)
class ChangePasswordRequest(BaseModel):
    current_password:str
    new_password:str=Field(min_length=8)# 
#=================================={Booking Schemas}=======================================
class BookingBase(BaseModel):
    title:str=Field(min_length=2,max_length=100)
    price:float=Field(gt=0)
    description:str=Field(max_length=255)
class BookingCreate(BookingBase):
    active:bool=True
class BookingUpdate(BookingBase):
    active:bool|None=None
class BookingPablic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    title:str
    price:float
    description:str
    active:bool
    created_at:datetime
    updated_at:datetime
# =================================={Block Schemas}========================================
class BlockBase(BaseModel):
    email:EmailStr=Field(max_length=120)
    name:str=Field(max_length=120)
class BlockCreate(BlockBase):
    reason:str|None=Field(max_length=300)
class BlockDelete(BaseModel):
    email:EmailStr=Field(max_length=120)
class BlockPablic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    email:EmailStr
    name:str
    reason:str|None
    created_at:datetime
# =================================={File Schemas}=======================================
class MedicalFileOut(BaseModel):
    id:UUID
    file_path:str
    kind:str
    is_new:bool
    created_at:datetime
# ================================={Appointment Schemas}=======================================
class AppointmentBase(BaseModel):
   date:date 
   time:time
class AppointmentCreate(AppointmentBase):
    type_id:UUID
    doctor_id:UUID
class AppointmentUpdate(AppointmentBase):
    status:AppointmentStatus|None=None 
class AppointmentPablic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    date:date
    time:time
    status:str
    appointment_type: str
    created_at:datetime
    client_name:str
# ================================={Dashboard Schemas}=======================================
class DashboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    files:list[MedicalFileOut]
    appointments:list[AppointmentPablic]
    total_New_files:int|None
    total_appointments:int
    total_New_Messages:int
# ==================================={Message Schemas}======================================
class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    conversation_id:UUID
    sender_id:UUID
    text:str
    created_at:datetime
# =================================={Conversation Schemas}======================================
class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    doctor_id:UUID
    client_id:UUID
    messages:list[MessageOut]
    