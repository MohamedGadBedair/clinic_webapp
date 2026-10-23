from fastapi import APIRouter, WebSocket, Query,Depends, WebSocketException,status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated
from uuid import UUID
import json

from database import get_db
from models import Conversation
from schemas import ConversationOut
from services.websocket_manager import manager
from auth import get_current_user,CurrentUser
from services.query_utils import get_user_conection_list,get_user_conversation
# ==============================={Routers}=================================
router = APIRouter()
# =============================={Chat API}=================================
@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)  # <-- Let FastAPI inject the database session properly
    ):
    # get the current user data
    current_user=await get_current_user(token, db)
    # bind the current user to the websocket
    await manager.connect(websocket,current_user,db)
    # get the list of users that the current user is allowed to be connected to
    user_list=await get_user_conection_list(current_user,db)
    # send the hello message
    await websocket.send_json({"message":"hello"})
    
    try:
        while True:
            # receive the message
            raw_data = await websocket.receive_text()
            
            # make sure the data is a valid JSON
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue  

            # get the recipient_id and content from the data
            recipient_id = UUID(data.get("recipient_id"))
            content = data.get("content")
            
            # check if the recipient_id and content are valid to send the message
            if recipient_id and content:
                if recipient_id not in user_list:
                    raise WebSocketException(code=400, reason="Invalid recipient_id")
                # get the conversation between the current user and the recipient   
                conversation = await get_user_conversation(current_user,recipient_id,db)
                        
                # send the message to the recipient if he is online or save it to the database
                await manager.send_direct_message(
                    conversation_id=conversation.id,
                    sender_id=current_user.id,
                    sender_role=current_user.role,
                    recipient_id=recipient_id,
                    content=content,
                    db=db
                )

    except WebSocketException as e:
        # send the error message to the client
        await websocket.send_json({"error": e.reason})

    except Exception as e:
        # send the error message to the client
        await websocket.send_json({"error": str(e)})

    finally:
        # remove the current user from the active connections
        await manager.disconnect(current_user,db)

@router.get('',status_code=status.HTTP_200_OK,response_model=list[ConversationOut])
async def get_user_conversations(db: Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    # get the list of conversations
    if current_user.role == "CLIENT":
        user_conversations=await db.execute(select(Conversation).where(Conversation.client_id==current_user.id).order_by(Conversation.created_at.desc()))
    elif current_user.role == "DOCTOR":
        user_conversations=await db.execute(select(Conversation).where(Conversation.doctor_id==current_user.id).order_by(Conversation.created_at.desc()))
    
    return user_conversations.scalars().all()
