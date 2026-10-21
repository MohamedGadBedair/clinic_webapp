from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query,Depends, WebSocketException
import json
from uuid import UUID

from websocket_manager import manager
from auth import get_current_user
from database import get_db
from services.query_utils import get_user_conection_list,get_user_conversation
router = APIRouter()

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)  # <-- Let FastAPI inject the database session properly
    ):
    
    current_user=await get_current_user(token, db)
    await manager.connect(websocket,current_user,db)

    user_list=await get_user_conection_list(current_user,db)

    await websocket.send_json({"message":"hello"})
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
                continue  
            
            recipient_id = UUID(data.get("recipient_id"))
            content = data.get("content")

            if recipient_id and content:
                if recipient_id not in user_list:
                    raise WebSocketException(code=400, reason="Invalid recipient_id")
                
                conversation = await get_user_conversation(current_user,recipient_id,db)
                        
                
                await manager.send_direct_message(
                    conversation_id=conversation.id,
                    sender_id=current_user.id,
                    sender_role=current_user.role,
                    recipient_id=recipient_id,
                    content=content,
                    db=db
                )

    except WebSocketDisconnect:
        await manager.disconnect(current_user,db)