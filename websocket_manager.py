import json
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query,Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Message

app = FastAPI()

class ChatManager:
    def __init__(self):
        # قاموس يربط معرف المستخدم بالـ WebSocket الخاص به
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_direct_message(self, sender_id: str, recipient_id: str, content: str):
        """إرسال الرسالة فوراً للمستقبل إذا كان أونلاين، وإلا يتم حفظها في قاعدة البيانات"""
        recipient_ws = self.active_connections.get(recipient_id)
        
        # تجهيز نص الرسالة بهيكل JSON مريح للمطور في الفرونت إند
        message_data = json.dumps({
            "sender_id": sender_id,
            "content": content,
            "timestamp": str(datetime.datetime.now())
        })

        if recipient_ws:
            # السيناريو الأول: المستخدم الآخر متصل (Online) -> أرسل له مباشرة
            try:
                await recipient_ws.send_text(message_data)
                # (اختياري) يمكنك أيضاً حفظها هنا في قاعدة البيانات كـ "مقروءة" للتوثيق الإضافي
            except Exception:
                self.disconnect(recipient_id)
                self.save_to_db(sender_id, recipient_id, content, is_read=False)
        else:
            # السيناريو الثاني: المستخدم الآخر غير متصل (Offline) -> احفظ في قاعدة البيانات فوراً
            self.save_to_db(sender_id, recipient_id, content, is_read=False)

    async def save_to_db(self, sender_id: str, recipient_id: str, content: str, is_read: bool,db:Annotated[AsyncSession, Depends(get_db)]):
        """دالة مساعدة لفتح جلسة قاعدة البيانات وحفظ الرسالة"""
        db_message = Message(sender_id=sender_id, recipient_id=recipient_id, content=content, is_read=is_read)
        db.add(db_message)
        await db.commit()

manager = ChatManager()
