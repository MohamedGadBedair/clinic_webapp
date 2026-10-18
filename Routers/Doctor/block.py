
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BlockedEmail,User
from database import get_db

from schemas import (
    BlockCreate,
    BlockDelete,
    BlockPablic
    )

from auth import CurrentDoctor

# =================================={Routers}==========================================
router = APIRouter()
# ==============================={Boocking API}========================================
# Get Block List API
@router.get(
    '/',
    status_code=status.HTTP_200_OK,
    response_model=list[BlockPablic]
    )
async def block_list(db: Annotated[AsyncSession,Depends(get_db)], current_Doctor:CurrentDoctor):
    blocks_q = await db.execute(select(BlockedEmail).where(BlockedEmail.doctor_id == current_Doctor.id))
    blocks = blocks_q.scalars().all()
    return blocks

# Create Block API
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=BlockPablic)
async def bock_user(data: BlockCreate, db: Annotated[AsyncSession,Depends(get_db)], current_Doctor:CurrentDoctor):
    
        # check if the user_email is blocked
    blocked_q = await db.execute(select(BlockedEmail).where(BlockedEmail.email == data.email))
    blocked = blocked_q.scalars().first()
    if blocked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email {data.email} is already blocked.")
    # check if the user_email is doctor email
    doctors_email_q = await db.execute(select(User).where(User.email == data.email, User.role == "DOCTOR"))
    doctors_email = doctors_email_q.scalars().first()
    if doctors_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Email {data.email} belongs to a doctor and cannot be blocked.")
    
    # Create a new booking in the database
    new_block = BlockedEmail(**data.model_dump())
    new_block.doctor_id = current_Doctor.id
    db.add(new_block)
    await db.commit()
    await db.refresh(new_block)

    return new_block

# Delete Block API
@router.delete("/delete/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(block_id: UUID, db: Annotated[AsyncSession,Depends(get_db)], current_Doctor: CurrentDoctor):
      
    # Fetch the block from the database
    block_q = await db.execute(select(BlockedEmail).where(BlockedEmail.id == block_id))
    block = block_q.scalars().first()

    # Check if the booking exists
    if not block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Block with id {block_id} not found.")
    

    # Check if the current doctor is authorized to unblock this email
    if block.doctor_id != current_Doctor.id:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to delete this block.") 


    # Delete the booking from the database
    await db.delete(block)
    await db.commit()