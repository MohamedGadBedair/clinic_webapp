from typing import Annotated
from datetime import timedelta ,UTC, datetime

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Request,APIRouter, HTTPException, status, Depends, BackgroundTasks

from authlib.integrations.starlette_client import OAuthError

from sqlalchemy import select, func,delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User,PasswordResetToken,ValidateEmailToken
from database import get_db

from schemas import (
    UserCreate,
    Token,
    ForgotPasswordRequest,
    ResetPasswordRequest
    )

from auth import(
    create_access_token,
    hash_password,
    verify_password,
    hashed_secret_token,
    genetate_secret_token
)

from services.email_utils import(
     send_password_reset_email,
     send_email_validation_email,
     oauth,
)

router = APIRouter()

# ===================================={User Auth API's}====================================
# register User API
@router.post(
        '/',
        status_code=status.HTTP_201_CREATED
        )
async def register(
    user:UserCreate,
    db:Annotated[AsyncSession,Depends(get_db)],
    background_task:BackgroundTasks
    ):
    
    # see if user name used or not 
    existing_username_q=await db.execute(select(User).where(func.lower(User.username)==user.username.strip().lower()))
    existing_username=existing_username_q.scalars().first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="this user already exist"
            )
   
    # see if user email used or not 
    existing_useremail_q= await db.execute(select(User).where(func.lower(User.email)==user.email.strip().lower()))
    existing_useremail=existing_useremail_q.scalars().first()
    if existing_useremail:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="this user already exist"
            )
    # create new user
    new_user =User(
        username=user.username.strip().lower(),
        email=user.email.strip().lower(),
        password_hash=hash_password(user.password)
        )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # send email validation link
    token = genetate_secret_token()
    token_hash=hashed_secret_token(token)
    expires_at=datetime.now(UTC)+timedelta(minutes=settings.reset_token_expire_minutes)

    reset_token=ValidateEmailToken(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=expires_at
        )
    
    db.add(reset_token)
    await db.commit()

    background_task.add_task( 
        send_email_validation_email,
        to_email=new_user.email,
        username=new_user.username,
        token=token
        )
    print(f'token:{token}')
    print(f'token_hash:{token_hash}')

    return{
        'message':'check your email, you will recive vialidation instructions.'
    }
@router.get('/vialidate_email/{token}',status_code=status.HTTP_200_OK)
async def validate_email(
    token:str,
    db:Annotated[AsyncSession,Depends(get_db)]):

    hash_token=hashed_secret_token(token)
    print(hash_token)
    hash_token_q=await db.execute(select(ValidateEmailToken).where(ValidateEmailToken.token_hash==hash_token).order_by(ValidateEmailToken.created_at.asc()))
    hash_token=hash_token_q.scalars().first()
    print(hash_token)
    if not hash_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')
    
    if hash_token.expires_at<datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')

    user_q=await db.execute(select(User).where(User.id==hash_token.user_id))
    user=user_q.scalars().first()

    if not user:
       raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')

    user.validated=True
    await db.execute(sql_delete(ValidateEmailToken).where(ValidateEmailToken.user_id==user.id))

    await db.commit()
    return{
        'message': 'Email validated successfully. you can log in with your email.'
    }
# login via google
@router.get("/login/google")
async def login_via_google(request: Request):
    """Initiate the Google OAuth2 login flow."""
    redirect_uri = request.url_for('auth_callback')
    print(f"Generated Redirect URI for Google: {redirect_uri}") 
    return await oauth.google.authorize_redirect(request, redirect_uri)
@router.get("/google/callback", name="auth_callback",response_model=Token)
async def auth_callback(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    """Callback endpoint that Google redirects to after authentication."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth error: {error.error}")
    
    user_info = token.get('userinfo')

    if not user_info:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User info not found in token")
    
    username = user_info.get('name')
    email = user_info.get('email')
    user_img= user_info.get('picture')
    
    if not email:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not found in user info")

    user_q = await db.execute(select(User).where(User.email == email))
    user=user_q.scalars().first()
    if not user:
        user = User(email=email, username=username, password_hash=None,validated=True)
        if user_img:
            user.user_profile_img=user_img


    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(data={'user_id': str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
# login API
@router.post(
        '/token',
        response_model=Token,
        status_code=status.HTTP_200_OK
        )
async def login_for_access_token(
    form_data:Annotated[OAuth2PasswordRequestForm,Depends()],
    db:Annotated[AsyncSession,Depends(get_db)]
    ):
    
    # get user from database
    result=await db.execute(select(User).where(func.lower(User.email)==form_data.username.lower()))
    user=result.scalars().first()

    # verfiy user exists and password is correct
    if not user or not verify_password(form_data.password,user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate':'Bearer'}
            )
    
    # check if user email is validated
    if not user.validated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Email not validated. Please vialidate your email first.',
            headers={'WWW-Authenticate':'Bearer'}
            )

    # create access token with user id as subject
    access_token_expires=timedelta(minutes=settings.access_token_expire_minutes)
    access_token=create_access_token(data={'sub':str(user.id)},expires_delta= access_token_expires)
    
    return Token(access_token=access_token,token_type='bearer')
# get current user
# ====================================={Password API's}======================================
@router.post('/forgot_password',status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data:ForgotPasswordRequest,
    background_task:BackgroundTasks,
    db:Annotated[AsyncSession,Depends(get_db)]
):
    user_q=await db.execute(select(User).where(func.lower(User.email)==request_data.email.strip().lower()))
    user=user_q.scalars().first()

    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid email')

    if user:
        await db.execute(sql_delete(PasswordResetToken).where(PasswordResetToken.user_id==user.id))

    token = genetate_secret_token()
    token_hash=hashed_secret_token(token)
    expires_at=datetime.now(UTC)+timedelta(minutes=settings.reset_token_expire_minutes)

    reset_token=PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
        )
    
    db.add(reset_token)
    await db.commit()

    background_task.add_task( 
        send_password_reset_email,
        to_email=user.email,
        username=user.username,
        token=token
        )

    return{
        'message':'if an account exists with this email, you will recive password reset instructions.'
    }
@router.post('/reset_password',status_code=status.HTTP_200_OK)
async def reset_password(
    request_data:ResetPasswordRequest,
    db:Annotated[AsyncSession,Depends(get_db)]):

    hash_token=hashed_secret_token(request_data.token)

    hash_token_q=await db.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash==hash_token).order_by(PasswordResetToken.created_at.asc()))
    hash_token=hash_token_q.scalars().first()

    if not hash_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')
    
    if hash_token.expires_at<datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')

    user_q=await db.execute(select(User).where(User.id==hash_token.user_id))
    user=user_q.scalars().first()

    if not user:
       raise HTTPException(status.HTTP_400_BAD_REQUEST,'Invalid or expired token')

    user.password_hash=hash_password(request_data.new_password)

    await db.execute(sql_delete(PasswordResetToken).where(PasswordResetToken.user_id==user.id))

    await db.commit()
    return{
        'message': 'password reset successfully. you can log in with your new password.'
    }
