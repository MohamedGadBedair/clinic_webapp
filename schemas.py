from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime,date,time
from lists import(
    UserRole,
    Gender,
    MedicalFileType,
    MessageStatus,
    City
)



#================================={User Schemas}==========================
class UserBase(BaseModel):
    username:str = Field(min_length=2,max_length=50)
    email:EmailStr=Field(max_length=100)

class UserCreate(UserBase):
    role:UserRole=Field()
    doctor_id:int|None=Field(default=None)
    password:str = Field(min_length=8)
class UserUpdate(BaseModel):
    username: str|None = Field(default=None,min_length=2,max_length=50)
    email: EmailStr|None = Field(default=None,max_length=100)
    description: str|None = Field(default=None,max_length=255)
    dob: date|None = Field(default=None)
    phone: str = Field(pattern=r"^\+?[1-9]\d{1,14}$", description="رقم الهاتف بصيغة دولية")
    city:City|None = Field(default=None)
class UserPablic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username:str 
    image_file: str|None
    image_path: str
class UserPrivate(UserBase): 
    email:EmailStr
    description: str|None = Field(default=None,max_length=255)
    dob: date|None = Field(default=None)
    phone: str = Field(pattern=r"^\+?[1-9]\d{1,14}$", description="رقم الهاتف بصيغة دولية")
    city:City|None = Field(default=None)
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

