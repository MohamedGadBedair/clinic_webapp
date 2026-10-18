from typing import Annotated
from datetime import date

from fastapi import APIRouter, status, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Appointment, MedicalFile
from database import get_db

from schemas import (
    DashboardOut
    )

from auth import CurrentUser
from lists import AppointmentStatus

# ====================={Routers}===============================
router = APIRouter()
# ==================={Appointment API}============================
# get dashboard API
@router.get('/dashboard',status_code=status.HTTP_200_OK)
async def get_dashboard(db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    today = date.today()
    if current_user.role == "DOCTOR":
        appointment_q=select(Appointment).where(Appointment.doctor_id==current_user.id).where(Appointment.date >= today)
        files_q=select(MedicalFile).where(MedicalFile.doctor_id==current_user.id)
    else:
        appointment_q=select(Appointment).where(Appointment.client_id==current_user.id)
        files_q=select(MedicalFile).where(MedicalFile.client_id==current_user.id)

    appointments_exec = await db.execute(appointment_q)
    appointments = appointments_exec.scalars().all()
    files_exec = await db.execute(files_q)
    files = files_exec.scalars().all()
    # get total appointments
    total_appointments = sum(
        1 for app in appointments 
        if app.status not in ("CANCELLED", "COMPLETED")
        )
    total_New_files=None
    if current_user.role == "DOCTOR":
        # get total new files if user is doctor
        total_New_files = sum(
            1 for file in files 
            if file.is_new == True
        )

    
    return DashboardOut.model_validate({"files":files,"appointments":appointments,"total_New_files":total_New_files,"total_appointments":total_appointments})