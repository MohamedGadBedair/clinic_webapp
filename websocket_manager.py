import json
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, WebSocket,Depends,WebSocketException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Message,Conversation,User

app = FastAPI()

class ChatManager:
    def __init__(self):
        # list of active connections
        self.active_connections: dict[str, WebSocket] = {}
    
    # func bild a connection 
    async def connect(self, websocket: WebSocket, current_user:User,db:Annotated[AsyncSession,Depends(get_db)]):
        # check if the user is already connected
        if current_user.id in self.active_connections.keys():
            raise WebSocketException(code=400,reason="User already connected")
        # build the connection and add the user to the active connections list
        await websocket.accept()
        self.active_connections[current_user.id] = websocket
        # update the user status
        current_user.is_online=True
        await db.commit()
    
    # func close the connection
    async def disconnect(self,current_use:User,db:Annotated[AsyncSession,Depends(get_db)]):
        # check if the user is connected
        if current_use.id in self.active_connections.keys():
            del self.active_connections[current_use.id]
        # update the user status
        current_use.is_online = False
        await db.commit()
    
    # func send message from the sender to the recipient
    async def send_direct_message(self,conversation_id: str, sender_id: str,sender_role: str, recipient_id: str, content: str, db:Annotated[AsyncSession, Depends(get_db)]):
                
        # prepare the message
        message_data = json.dumps({
            "sender_id": str(sender_id),
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "conversation_id": str(conversation_id)
        })

        # send the message to the recipient if he is connected else save it to the database
        recipient_ws = self.active_connections.get(recipient_id)
        if recipient_ws:
            try:
                await recipient_ws.send_text(message_data)
            except Exception:
                await self.save_to_db(conversation_id=conversation_id,sender_id=sender_id,sender_role=sender_role, recipient_id=recipient_id, content=content, is_read=False, db=db)
        else:
           await self.save_to_db(conversation_id=conversation_id,sender_id=sender_id,sender_role=sender_role, recipient_id=recipient_id, content=content, is_read=False, db=db)
    
    # func save the message to the database
    async def save_to_db(self,conversation_id:str, sender_id: str,sender_role: str,recipient_id: str, content: str, is_read: bool,db:Annotated[AsyncSession, Depends(get_db)]):
        """دالة مساعدة لفتح جلسة قاعدة البيانات وحفظ الرسالة"""
        conversation_q = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = conversation_q.scalars().first()
        
        if sender_role == "CLIENT":
            conversation.doctor_unread += 1
        elif sender_role == "DOCTOR":
            conversation.client_unread += 1            
        
        db_message = Message(sender_id=sender_id, conversation_id=conversation_id, text=content)
        db.add(db_message)
        await db.commit()

manager = ChatManager()
