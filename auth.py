from datetime import UTC, datetime, timedelta
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from fastapi import HTTPException, Depends,status
from fastapi.security import OAuth2PasswordBearer

from models import User
from database import get_db

import jwt
from pwdlib import PasswordHash

import hashlib
import secrets

from config import settings

password_hash = PasswordHash.recommended()
oath2_scheme = OAuth2PasswordBearer(tokenUrl='api/authentication/login')

#=========================={Password Functions}============================
def hash_password(password:str)->str:
    return password_hash.hash(password)
def verify_password(plain_password:str,hashed_password:str)->bool:
    return password_hash.verify(plain_password,hashed_password)
#=========================={Token Functions}===============================
def create_access_token(data:dict,expires_delta:timedelta|None = None)->str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire =datetime.now(UTC)+expires_delta
    else:
        expire=datetime.now(UTC)+timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({'exp':expire})
    encoded_jwt=jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        settings.algorithm
        )
    
    return encoded_jwt

def verify_access_token(token:str)->str|None:
    """Verify aJWT access token and return the subject (user id) if valid."""
    try: 
        payload=jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            settings.algorithm,
            {'require':['exp','sub']})
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get('sub')
# ====================={Get Current User Function}===============================
async def get_current_user(
        token:Annotated[str,Depends(oath2_scheme)],
        db:Annotated[AsyncSession,Depends(get_db)]
        ):
    # get user_id form token
    user_id =verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
            headers={'WWW-Authenticate':'Bearer'}
        )
    # get user data from database by user_id
    result = await db.execute(select(User).where(User.id==user_id))
    current_user=result.scalars().first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='user not found',
            headers={'WWW-Authenticate':'Bearer'}
            )
    return current_user

CurrentUser=Annotated[User,Depends(get_current_user)]

# ======================{Reset Password Functions}=================================================
def genetate_secret_token()->str:
    return secrets.token_urlsafe(32)

def hashed_secret_token(token:str)->str:
    return hashlib.sha256(token.encode()).hexdigest()

