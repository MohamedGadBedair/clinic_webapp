from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

#================================={User Schemas}==========================
class UserBase(BaseModel):
    username:str = Field(min_length=2,max_length=50)
    email:EmailStr=Field(max_length=100)
class UserCreate(UserBase):
    password:str = Field(min_length=8)
class UserUpdate(BaseModel):
    username: str|None = Field(default=None,min_length=2,max_length=50)
    email: EmailStr|None = Field(default=None,max_length=100)
class UserPablic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username:str 
    image_file: str|None
    image_path: str
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
    new_password:str=Field(min_length=8)