

from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, UploadFile


from sqlalchemy import select, func,delete as sql_delete
from sqlalchemy.orm import load_only
from sqlalchemy.ext.asyncio import AsyncSession

from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from config import settings
from models import User
from database import get_db

from schemas import (
    UserUpdate,
    UserPablic,
    UserPrivate,
    ChangePasswordRequest,
    UserPrivate,
    )

from auth import CurrentUser,verify_password, hash_password

from services.image_utils import (
    delete_profile_image,
    process_profile_imge
)

router = APIRouter()
# =================================== {Users Control APIS} =======================================
# Get Current User API
@router.get(
        '/me',
        response_model=UserPrivate,
        status_code=status.HTTP_200_OK
        )
async def get_current_user(current_user:CurrentUser):
    """Get the currently authenticated user."""
    return current_user
# Get User API
@router.get(
    '/{user_id}',
    status_code=status.HTTP_200_OK,
    response_model=UserPablic
    )
async def get_user(user_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    user_q=await db.execute(select(User).where(User.id==user_id))
    user=user_q.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f'user with id {user_id} not found')
    
    return user
# Delete User API
@router.delete(
        "/",
        status_code=status.HTTP_204_NO_CONTENT
        )
async def delet_user(db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    old_filename =current_user.user_profile_img
    await db.delete(current_user)
    await db.commit()
    if old_filename:
        delete_profile_image(filename=old_filename)
# Update User Name&Email API
@router.patch(
    '/',
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UserPrivate
)
async def update_user(user_data:UserUpdate,db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    count= 0

    if user_data.username:
        if user_data.username.lower().strip() and user_data.username.lower().strip()!=current_user.username.lower().strip() :
            
            # see if user name used or not 
            existing_username_q=await db.execute(select(User).options(load_only(User.username)).where(func.lower(User.username)==user_data.username.lower().strip()))
            existing_username=existing_username_q.scalars().first()
            
            if existing_username:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'name: {user_data.username} already userd')
            else:
                current_user.username = user_data.username.lower().strip()
        else: count+=1
    if user_data.email:
        if user_data.email.lower().strip() and user_data.email.lower().strip()!=current_user.email.lower().strip() :
            
            # see if user email used or not 
            existing_useremail_q=await db.execute(select(User).where(func.lower(User.email)==user_data.email.lower().strip()))
            existing_useremail=existing_useremail_q.scalars().first()
        
            if existing_useremail:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'email: {user_data.email} already userd')
            else:
                current_user.email = user_data.email.lower().strip()
        else: count+=1

    if count == 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='no defferant in data to update')

    await db.commit()
    await db.refresh(current_user)
    return current_user
@router.patch('/me/password',status_code=status.HTTP_200_OK)
async def change_password(current_user:CurrentUser,request_data:ChangePasswordRequest,db:Annotated[AsyncSession,Depends(get_db)]):
    
    if not verify_password(request_data.current_password,current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,'invalid data')
    
    current_user.password_hash=hash_password(request_data.new_password)
    
    await db.commit()

    return{
        'message':'password changed successfully'
    }

# ================================{Profile Picture APIS}=================================
# # upload profile picture
@router.patch(
        '/picture',
        response_model=UserPrivate,
        status_code=status.HTTP_202_ACCEPTED
        )
async def upload_profile_picture(
    file: UploadFile,
    current_user:CurrentUser,
    db:Annotated[AsyncSession,Depends(get_db)]
):
    content=await file.read()

    if len(content)>settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'file is too large, maxmum size is {settings.max_upload_size_bytes//(1024*1024)}MB'
        )

    try:
        new_filename=await run_in_threadpool(process_profile_imge,content)
    
    except UnidentifiedImageError as err:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Invalid image. please upload a valid imge (JPEG,PNG,GIF,WebP)'
            )from err
    
    old_filename=current_user.user_profile_img
    current_user.user_profile_img =new_filename

    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return current_user
# delete profile picture
@router.delete(
        '/picture',
        status_code=status.HTTP_204_NO_CONTENT
        )
async def delete_profile_picture(
    current_user:CurrentUser,
    db:Annotated[AsyncSession,Depends(get_db)]
):
    if not current_user.user_profile_img:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'No profile picture to delete'
            )
    
    old_filename=current_user.user_profile_img

    current_user.user_profile_img=None
    await db.commit()
    await db.refresh(current_user)

    delete_profile_image(old_filename)
