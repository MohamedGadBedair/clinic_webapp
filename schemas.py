from pydantic import BaseModel, ConfigDict, Field, EmailStr,UUID4
from datetime import datetime,date,time
from uuid import UUID

from lists import(
    UserRole,
    Gender,
    MedicalFileType,
    MessageStatus,
    City
)



#====================================={User Schemas}===================================
class UserBase(BaseModel):
    username:str = Field(min_length=2,max_length=50)
    email:EmailStr=Field(max_length=100)

class UserCreate(UserBase):
    role:UserRole
    doctor_id:UUID
    password:str = Field(min_length=8)
class UserUpdate(BaseModel):
    username: str|None = Field(default=None,min_length=2,max_length=50)
    email: EmailStr|None = Field(default=None,max_length=100)
    description: str|None = Field(default=None,max_length=255)
    phone_code:str|None=Field(default="+20",pattern=r"^\+\d{1,4}$", description="رمز الدولة بصيغة دولية")
    phone: str|None = Field(pattern=r"^\+?[1-9]\d{1,14}$", description="رقم الهاتف بصيغة دولية")
    dob: date|None = Field(default=None)
    city:City|None = Field(default=None)
    gender:Gender|None=None
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


    model_config = ConfigDict(from_attributes=True)
class UserPrivate(UserPablic): 
    email:EmailStr
#================================={Token Schemas}==========================
class Token(BaseModel):
    access_token:str
    token_type:str
#================================={Reset Password Schemas}==========================
class ForgotPasswordRequest(BaseModel):
    email:EmailStr=Field(max_length=120)
class ResetPasswordRequest(BaseModel):
    token:str
    new_password:str=Field(min_length=8)
class ChangePasswordRequest(BaseModel):
    current_password:str
    new_password:str=Field(min_length=8)# 

