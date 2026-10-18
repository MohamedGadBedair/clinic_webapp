from typing import Annotated
from uuid import UUID
from datetime import date,time,timedelta

from fastapi import APIRouter, HTTPException, status, Depends,Form

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Appointment, User, BookingType
from database import get_db

from schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentPablic
    )

from auth import CurrentUser
from lists import AppointmentStatus

# ===================={Routers}===============================
router = APIRouter()
# ==================={Appointment API}============================
# get Appointment List API
@router.get(
    '/list',
    status_code=status.HTTP_200_OK,
    response_model=list[AppointmentPablic]
    )
async def get_appointment_list(
    db:Annotated[AsyncSession,Depends(get_db)],
    current_user:CurrentUser,
    skip:int=0,   
    limit:int= 10,
    date_from: date | None = None,
    date_to: date | None = None,
    status: AppointmentStatus | None = None,
    appointment_status: AppointmentStatus | None = None,
  ):
    if current_user.role == "DOCTOR":
        q = select(Appointment).where(Appointment.doctor_id == current_user.id )
    else:
        q = select(Appointment).where(Appointment.client_id == current_user.id )    

    if date_from:
        q = q.where(Appointment.date >= date_from)
    if date_to:
        q = q.where(Appointment.date <= date_to)
    if appointment_status:
        q = q.where(Appointment.status == appointment_status)

    if status:
        q = q.where(Appointment.status == status)
    
    appointment_q = await db.execute(q.offset(skip).limit(limit))
    appointment = appointment_q.scalars().all()
    return appointment
# create Appointment API
@router.post('/create',status_code=status.HTTP_201_CREATED,response_model=AppointmentPablic)
async def create_appointment(data:AppointmentCreate,db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    # check if user is a not a client
    if current_user.role != "CLIENT":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only clients can create an appointment.")
    
    # check if doctor exists
    doctor_q = await db.execute(select(User).where(User.id == data.doctor_id))
    doctor = doctor_q.scalars().first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"this Doctor with not found.")
    
    # check if booking type exists
    boking_type_q = await db.execute(select(BookingType).where(BookingType.id == data.type_id and BookingType.active == True))
    boking_type = boking_type_q.scalars().first()
    if not boking_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"this Booking Type with unavailable.")
    
    # check if appointment date is in the past
    if data.date < date.today() or (data.date == date.today() and data.time < time.now()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this date is in the past.")
    
    # Check if the appointment is already scheduled
    existing_appointment_q = await db.execute(select(Appointment).where(Appointment.date == data.date and Appointment.time in[data.time-timedelta(minutes=30),data.time,data.time+timedelta(minutes=30)] and Appointment.doctor_id == data.doctor_id))
    existing_appointment = existing_appointment_q.scalars().first()
    if existing_appointment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this appointment is already scheduled pls choose another time.")

    # create new appointment
    new_appointment = Appointment(**data.model_dump(),client_id=current_user.id)
    db.add(new_appointment)
    await db.commit()
    await db.refresh(new_appointment,[])
    return new_appointment  
# update Appointment API
@router.patch('/update/{appointment_id}',status_code=status.HTTP_200_OK,response_model=AppointmentPablic )
async def update_appointment(appointment_id:UUID,data:AppointmentUpdate,db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    
    # check if appointment exists 
    appointment_q = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = appointment_q.scalars().first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"this Appointment with not found.")
    
    # check if current user is the creator or the doctor
    if current_user.id != appointment.client_id and current_user.id != appointment.doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only the owner or the doctor can update an this appointment.")
    
    # Check if the appointment is already scheduled
    existing_appointment_q = await db.execute(select(Appointment).where(Appointment.date == data.date and Appointment.time in[data.time-timedelta(minutes=30),data.time,data.time+timedelta(minutes=30)] and Appointment.doctor_id == data.doctor_id))
    existing_appointment = existing_appointment_q.scalars().first()
    if existing_appointment and existing_appointment.id != appointment.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this appointment is already scheduled pls choose another time.")

    if appointment.status == "COMPLETED" or appointment.status == "CANCELLED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this appointment can't be updated.")
    if (data.status == "CANCELLED")or(data.status == "COMPLETED" and current_user.id == appointment.client_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this status updated is not allowed .")

    # Check if the appointment is already scheduled
    existing_appointment_q = await db.execute(select(Appointment).where(Appointment.date == data.date and Appointment.time in[data.time-timedelta(minutes=30),data.time,data.time+timedelta(minutes=30)] and Appointment.doctor_id == data.doctor_id))
    existing_appointment = existing_appointment_q.scalars().first()
    if existing_appointment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"this appointment is already scheduled pls choose another time.")
   
    # update appointment
    appointment.date = data.date
    appointment.time = data.time
    appointment.status = data.status
    await db.commit()
    await db.refresh(appointment)
    return appointment
# delete Appointment API
@router.delete('/delete/{appointment_id}',status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(appointment_id:UUID,db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    
    # check if appointment exists 
    appointment_q = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = appointment_q.scalars().first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"this Appointment with not found.")
    
    # check if current user is the creator
    if current_user.id != appointment.client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only the owner can cancel this appointment.")
    
    appointment.status = "CANCELLED"
    await db.commit()
    return