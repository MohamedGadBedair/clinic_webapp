import httpx
from fastapi import HTTPException
from config import settings

payment_secret_kay = settings.payment_secret_key.get_secret_value()
payment_methods = settings.payment_integration_id

async def create_paymob_intention(amount: float, user_email: str, user_phone: str, merchant_order_id: str):
    """
    دالة لإنشاء طلب دفع (Intention) على Paymob
    """

    url = "https://accept.paymob.com/v1/intention/"  # رابط الـ API الحديث لـ Paymob
    
    headers = {
        "Authorization": f"Bearer {payment_secret_kay}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": int(amount * 100),  # Paymob بتحسب المبلغ بالقروش (اضرب في 100)
        "currency": "EGP",
        "payment_methods": [int(payment_methods)], # معرف وسيلة الدفع
        "items": [
            {
                "name": "Clinic Appointment",
                "amount": int(amount * 100),
                "description": "Booking reservation fee",
                "quantity": 1
            }
        ],
        "billing_data": {
            "apartment": "NA",
            "email": user_email,
            "floor": "NA",
            "first_name": "Patient",
            "last_name": "User",
            "street": "NA",
            "building": "NA",
            "phone_number": user_phone,
            "shipping_method": "NA",
            "postal_code": "NA",
            "city": "Cairo",
            "country": "EG",
            "state": "Cairo"
        },
        "merchant_order_id": merchant_order_id,
        "redirection_url": "http://localhost:3000/payment-success" 
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail=f"Paymob Error: {response.text}")
            
        data = response.json()
        
        return data 