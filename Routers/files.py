from typing import Annotated
from uuid import UUID 

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File,Form

from lists import MedicalFileType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.concurrency import run_in_threadpool
from models import MedicalFile
from database import get_db

from config import settings
from services.files_utils  import (
    process_client_files,
    delete_client_file
)

from schemas import (
    MedicalFileOut
)
from auth import CurrentUser

router = APIRouter()

# ====================={Routers}===============================
router = APIRouter()
# ==================={Files API}============================

# Read Client Files API
@router.get('/',response_model=list[MedicalFileOut],status_code=status.HTTP_200_OK)
async def get_files(current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    # return client files
    if current_user.role =="CLIENT":
        files_q=await db.execute(select(MedicalFile).where(MedicalFile.client_id==current_user.id)) 
        files=files_q.scalars().all()
        return files
    # return doctor client files 
    if current_user.role =="DOCTOR":
        files_q=await db.execute(select(MedicalFile).where(MedicalFile.doctor_id==current_user.id)) 
        files=files_q.scalars().all()
        return files
    
# Upload Client Files API
@router.post('/upload',status_code=status.HTTP_201_CREATED,response_model=MedicalFileOut)
async def upload_files(kind:Annotated[MedicalFileType,Form()],client_file:Annotated[UploadFile,File()],doctor_id:Annotated[UUID,Form()],current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    # check if current user is authorized to upload files
    if current_user.role == "DOCTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Doctors can't upload files")
    
    # check if the file is valid
    if client_file.content_type not in ['image/jpeg','image/png','image/gif','image/webp','application/pdf','application/word']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid file extension")
    if client_file.content_type in ['image/jpeg','image/png','image/gif','image/webp']:
        kind="IMAGE"
    # check if the file is too large
    if client_file.size>settings.max_upload_size_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"File is too large, maximum size is {settings.max_upload_size_bytes//(1024*1024)}MB")
    
    # process the file
    filename=await run_in_threadpool(process_client_files,client_file.file.read(),client_file.content_type)
    # save the file 
    new_file=MedicalFile(
        filename=filename,
        kind=kind,
        client_id=current_user.id,
        doctor_id=doctor_id
        )
    
    db.add(new_file)
    await db.commit()
    
    return new_file

# Delete Client Files API
@router.delete('/delete/{file_id}',status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id:UUID, current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):

    file_q=await db.execute(select(MedicalFile).where(MedicalFile.id==file_id))
    file=file_q.scalars().first()
    # check if file exists
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f'File with id {file_id} not found')
    
    file_name=file.filename

    # check if current user is authorized to delete this file
    if file.client_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=f'You are not authorized to delete this file')
    
    await db.delete(file)
    await db.commit()
    
    delete_client_file(file_name)
