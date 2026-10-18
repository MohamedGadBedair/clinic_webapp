from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BookingType, DoctorClient
from database import get_db

from schemas import (
    BookingCreate,
    BookingUpdate,
    BookingPablic
    )

from auth import CurrentDoctor,CurrentUser

# ===================={Routers}===============================
router = APIRouter()
# ==================={Booking API}============================
# get Booking List API
@router.get("/{doctor_id}", status_code=status.HTTP_200_OK, response_model=list[BookingPablic])
async def booking_list(doctor_id: UUID,db: Annotated[AsyncSession,Depends(get_db)], current_user:CurrentUser):
    
    # check if the current doctor is authorized to view the booking type
    if current_user.id != doctor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this booking type.")
    
    # check if the current user is a client for the given doctor
    if current_user.role == "CLIENT":
        client_q = await db.execute(select(DoctorClient).where(DoctorClient.client_id == current_user.id, DoctorClient.doctor_id == doctor_id))
        client = client_q.scalars().first()
        if not client:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view this booking type.")
   
    # Fetch the booking from the database
    booking_q = await db.execute(select(BookingType).where(BookingType.doctor_id == doctor_id))
    booking = booking_q.scalars().all()
    
    return booking
# Create Booking Type API
@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=BookingPablic)
async def create_booking(data: BookingCreate, db: Annotated[AsyncSession,Depends(get_db)], current_Doctor:CurrentDoctor):
    
    # Create a new booking in the database
    new_booking = BookingType(**data.model_dump())
    new_booking.doctor_id = current_Doctor.id
    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)

    return new_booking

# Update Booking Type API
@router.patch("/update/{booking_id}", status_code=status.HTTP_200_OK, response_model=BookingPablic)
async def update_booking(booking_id: UUID, data: BookingUpdate, db: Annotated[AsyncSession,Depends(get_db)], current_Doctor: CurrentDoctor):
   
    # Fetch the booking from the database
    booking_q = await db.execute(select(BookingType).where(BookingType.id == booking_id, BookingType.doctor_id == current_Doctor.id))
    booking = booking_q.scalars().first()

    # Check if the booking exists
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking with id {booking_id} not found.")

    # Check if the bookingtype belongs to the current doctor
    if booking.doctor_id != current_Doctor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to update this booking type.")    

    # Update the booking fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)

    await db.commit()
    await db.refresh(booking)

    return booking

# Delete Booking Type API
@router.delete("/delete/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(booking_id: UUID, db: Annotated[AsyncSession,Depends(get_db)], current_Doctor: CurrentDoctor):
    
    # Fetch the booking from the database
    booking_q = await db.execute(select(BookingType).where(BookingType.id == booking_id))
    booking = booking_q.scalars().first()

    # Check if the booking exists
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Booking with id {booking_id} not found.")
    
    # Check if the bookingtype belongs to the current doctor
    if booking.doctor_id != current_Doctor.id:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to delete this booking type.") 

    # Delete the booking from the database
    await db.delete(booking)
    await db.commit()
