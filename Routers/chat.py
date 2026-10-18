import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status, Query, APIRouter
from  websocket_manager import manager

from auth import CurrentUser

router = APIRouter()

@router.websocket("/ws")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    user:CurrentUser
    ):
    websocket.send_json({"message":"hello"})
    # 1. تسجيل دخول المستخدم الحالي وتثبيته أنه "متصل"
    await manager.connect(user.id, websocket)
    
    try:
        while True:
            # 2. استقبال الرسائل القادمة من هذا المستخدم
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            
            recipient_id = data.get("recipient_id")
            content = data.get("content")
            
            if recipient_id and content:
                # 3. توجيه الرسالة عبر المدير للطرف الثاني
                await manager.send_direct_message(
                    sender_id=user.id, 
                    recipient_id=recipient_id, 
                    content=content
                )
                
    except WebSocketDisconnect:
        # 4. عند قطع الاتصال، يتم مسحه من القاموس النشط فقط
        # وبذلك أي رسالة قادمة له لاحقاً ستذهب تلقائياً لقاعدة البيانات
        manager.disconnect(user.id)
