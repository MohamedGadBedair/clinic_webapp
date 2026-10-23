from datetime import date, time, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Appointment, BookingType
from tests.api_helpers import auth_headers, make_user


@pytest.mark.anyio
async def test_client_can_list_and_cancel_own_appointment(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    patient = await make_user(db_session, role="CLIENT")
    booking = BookingType(doctor_id=doctor.id, title="Consultation", price=100, description="Visit")
    db_session.add(booking)
    await db_session.flush()
    appointment = Appointment(
        doctor_id=doctor.id,
        client_id=patient.id,
        type_id=booking.id,
        date=date.today() + timedelta(days=1),
        time=time(10, 0),
    )
    db_session.add(appointment)
    await db_session.commit()

    listed = await client.get("/api/clients/appointments/list", headers=auth_headers(patient))
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == str(appointment.id)

    deleted = await client.delete(
        f"/api/clients/appointments/delete/{appointment.id}", headers=auth_headers(patient)
    )
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_only_clients_can_create_appointments(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")

    response = await client.post(
        "/api/clients/appointments/create",
        headers=auth_headers(doctor),
        json={"doctor_id": str(doctor.id), "type_id": str(doctor.id), "date": "2099-01-01", "time": "10:00:00"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_appointment_list_requires_authentication(client: AsyncClient):
    response = await client.get("/api/clients/appointments/list")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_updating_an_unknown_appointment_returns_not_found(client: AsyncClient, db_session: AsyncSession):
    patient = await make_user(db_session, role="CLIENT")
    response = await client.patch(
        f"/api/clients/appointments/update/{uuid4()}",
        headers=auth_headers(patient),
        json={"date": "2099-01-01", "time": "10:00:00", "status": "pending"},
    )
    assert response.status_code == 404
