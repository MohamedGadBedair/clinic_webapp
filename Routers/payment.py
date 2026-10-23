from typing import Annotated

from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Depends, status

from database import get_db 
from auth import CurrentUser
from models import Appointment, Payment, User
from services.payment_utils import create_paymob_intention

router = APIRouter()

@router.post("")
async def pay_for_appointment(appointment_id: str,db: Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    
    appointment_data_q = await db.execute(select(Appointment).where(appointment_data==appointment_id))
    appointment_data = appointment_data_q.scalars().first()
    doctor_data_q = await db.execute(select(User.email).where(User.id==appointment_data.doctor_id))
    client_data_q =  await db.execute(select(User.email).where(User.id==appointment_data.client_id))
    doctor_data = doctor_data_q.scalars().first()
    client_data = client_data_q.scalars().first()
    
    if not appointment_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='appointment not found')

    # 2. أنشئ طلب الدفع على Paymob
    try:
        payment_response = await create_paymob_intention(
            amount=(appointment_data.type.price/5),
            user_email=current_user.email,
            user_phone=current_user.phone,
            merchant_order_id=appointment_id
        )
        
        new_payment=Payment(
            appointment_id=appointment_data.id,
            doctor_email=doctor_data,
            client_email=client_data,
            amount=appointment_data.appointment_price/5
            )
        
        db.add(new_payment)
        await db.commit()
        
        # Paymob بترجع رابط (redirection_url أو client_secret) يعرض صفحة الدفع
        return {
            "status": "success",
            "payment_data": payment_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def paymob_webhook(payload: dict,db: Annotated[AsyncSession,Depends(get_db)]):
    """
    الـ Webhook ده بيكلمه سيرفر Paymob أوتوماتيك أول ما العميل يدفع بنجاح
    علشان تحدث حالة الحجز في قاعدة البيانات عندك من pending لـ confirmed
    """

    obj = payload.get("obj", {})
    success = obj.get("success")
    merchant_order_id = obj.get("order", {}).get("merchant_order_id")
    if success:
        await db.execute(update(Appointment).where(Appointment.id==merchant_order_id).values(Appointment.status=='WAITING'))
        await db.execute(update(Payment).where(Payment.appointment_id==merchant_order_id).values(Payment.status=='COMPLETED'))
        return {"status": "received"}
        
    await db.execute(update(Payment).where(Payment.appointment_id==merchant_order_id).values(Payment.status=='failed'))
    return {"status": "failed"}