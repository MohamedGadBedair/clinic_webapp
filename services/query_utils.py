from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import DoctorClient,Conversation


async def get_user_conection_list(current_user,db:Annotated[AsyncSession,Depends(get_db)]):
    
    if current_user.role == "CLIENT":
        doctor_client_q = await db.execute(select(DoctorClient).where(DoctorClient.client_id == current_user.id))
        doctor_client = doctor_client_q.scalars().all()
        user_list = [client.doctor_id for client in doctor_client]
    
    if current_user.role == "DOCTOR":
        doctor_client_q = await db.execute(select(DoctorClient).where(DoctorClient.doctor_id == current_user.id))
        doctor_client = doctor_client_q.scalars().all()
        user_list = [client.client_id for client in doctor_client]

    return user_list

async def get_user_conversation(current_user,recipient_id,db:Annotated[AsyncSession,Depends(get_db)]):
    
    if current_user.role == "DOCTOR":
        conversation_id = await db.execute(select(Conversation).where(Conversation.doctor_id == current_user.id, Conversation.client_id == recipient_id))
        conversation= conversation_id.scalars().first()
        
        if not conversation:
            new_conversation = Conversation(doctor_id=current_user.id, client_id=recipient_id)
            db.add(new_conversation)
            await db.commit()
            await db.refresh(new_conversation)
            conversation = new_conversation

    elif current_user.role == "CLIENT":
        conversation_q = await db.execute(select(Conversation).where(Conversation.client_id == current_user.id, Conversation.doctor_id == recipient_id))
        conversation= conversation_q.scalars().first()
        if not conversation:
            new_conversation = Conversation(doctor_id=recipient_id, client_id=current_user.id)
            db.add(new_conversation)
            await db.commit()
            await db.refresh(new_conversation)
            conversation = new_conversation


    return conversation