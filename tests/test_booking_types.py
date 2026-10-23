from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api_helpers import auth_headers, make_user


BOOKING = {"title": "Consultation", "price": 250, "description": "Initial visit", "active": True}


@pytest.mark.anyio
async def test_doctor_can_create_update_list_and_delete_booking_type(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    headers = auth_headers(doctor)

    created = await client.post("/api/doctors/bookingtypes/create", headers=headers, json=BOOKING)
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]

    listed = await client.get(f"/api/doctors/bookingtypes/{doctor.id}", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [booking_id]

    updated = await client.patch(f"/api/doctors/bookingtypes/update/{booking_id}", headers=headers, json={**BOOKING, "price": 300})
    assert updated.status_code == 200
    assert updated.json()["price"] == 300

    deleted = await client.delete(f"/api/doctors/bookingtypes/delete/{booking_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_booking_type_routes_reject_clients(client: AsyncClient, db_session: AsyncSession):
    client_user = await make_user(db_session, role="CLIENT")
    response = await client.post("/api/doctors/bookingtypes/create", headers=auth_headers(client_user), json=BOOKING)
    assert response.status_code == 403


@pytest.mark.anyio
async def test_booking_type_creation_requires_authentication(client: AsyncClient):
    response = await client.post("/api/doctors/bookingtypes/create", json=BOOKING)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_booking_type_list_requires_authentication(client: AsyncClient):
    response = await client.get(f"/api/doctors/bookingtypes/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_booking_type_creation_rejects_invalid_payload(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    response = await client.post(
        "/api/doctors/bookingtypes/create",
        headers=auth_headers(doctor),
        json={"title": "x", "price": 0, "description": ""},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_doctor_cannot_create_a_second_booking_type(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    headers = auth_headers(doctor)
    assert (await client.post("/api/doctors/bookingtypes/create", headers=headers, json=BOOKING)).status_code == 201

    response = await client.post("/api/doctors/bookingtypes/create", headers=headers, json=BOOKING)
    assert response.status_code == 400
    assert response.json()["detail"] == "this type name aready used"


@pytest.mark.anyio
async def test_booking_type_update_and_delete_return_not_found_for_unknown_id(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    headers = auth_headers(doctor)

    update = await client.patch(f"/api/doctors/bookingtypes/update/{uuid4()}", headers=headers, json=BOOKING)
    delete = await client.delete(f"/api/doctors/bookingtypes/delete/{uuid4()}", headers=headers)

    assert update.status_code == 404
    assert delete.status_code == 404


@pytest.mark.anyio
async def test_doctor_cannot_list_another_doctors_booking_types(client: AsyncClient, db_session: AsyncSession):
    owner = await make_user(db_session, role="DOCTOR")
    other_doctor = await make_user(db_session, role="DOCTOR")
    response = await client.get(f"/api/doctors/bookingtypes/{owner.id}", headers=auth_headers(other_doctor))
    assert response.status_code == 403


@pytest.mark.anyio
async def test_doctor_cannot_update_or_delete_another_doctors_booking_type(client: AsyncClient, db_session: AsyncSession):
    owner = await make_user(db_session, role="DOCTOR")
    other_doctor = await make_user(db_session, role="DOCTOR")
    created = await client.post("/api/doctors/bookingtypes/create", headers=auth_headers(owner), json=BOOKING)
    booking_id = created.json()["id"]

    update = await client.patch(f"/api/doctors/bookingtypes/update/{booking_id}", headers=auth_headers(other_doctor), json=BOOKING)
    delete = await client.delete(f"/api/doctors/bookingtypes/delete/{booking_id}", headers=auth_headers(other_doctor))

    assert update.status_code == 404
    assert delete.status_code == 403
