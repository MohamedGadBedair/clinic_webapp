from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api_helpers import auth_headers, make_user


@pytest.mark.anyio
async def test_doctor_can_create_list_and_remove_a_block(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    headers = auth_headers(doctor)
    payload = {"email": "blocked@example.com", "name": "Blocked patient", "reason": "No-show"}

    created = await client.post("/api/doctors/blocked/create", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    block_id = created.json()["id"]

    listed = await client.get("/api/doctors/blocked/", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["email"] == payload["email"]

    deleted = await client.delete(f"/api/doctors/blocked/delete/{block_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.anyio
async def test_blocked_email_cannot_be_added_twice(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    headers = auth_headers(doctor)
    payload = {"email": "duplicate@example.com", "name": "Patient", "reason": None}
    assert (await client.post("/api/doctors/blocked/create", headers=headers, json=payload)).status_code == 201
    response = await client.post("/api/doctors/blocked/create", headers=headers, json=payload)
    assert response.status_code == 400


@pytest.mark.anyio
async def test_blocked_email_routes_require_a_doctor(client: AsyncClient, db_session: AsyncSession):
    patient = await make_user(db_session, role="CLIENT")
    response = await client.get("/api/doctors/blocked/", headers=auth_headers(patient))
    assert response.status_code == 403


@pytest.mark.anyio
async def test_blocked_email_creation_requires_authentication(client: AsyncClient):
    response = await client.post(
        "/api/doctors/blocked/create",
        json={"email": "blocked@example.com", "name": "Patient", "reason": None},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_blocked_email_creation_rejects_invalid_payload(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    response = await client.post(
        "/api/doctors/blocked/create",
        headers=auth_headers(doctor),
        json={"email": "not-an-email", "name": "", "reason": "x" * 301},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_doctor_email_cannot_be_blocked(client: AsyncClient, db_session: AsyncSession):
    owner = await make_user(db_session, role="DOCTOR")
    doctor_to_block = await make_user(db_session, role="DOCTOR")
    response = await client.post(
        "/api/doctors/blocked/create",
        headers=auth_headers(owner),
        json={"email": doctor_to_block.email, "name": "Doctor", "reason": None},
    )
    assert response.status_code == 400
    assert "belongs to a doctor" in response.json()["detail"]


@pytest.mark.anyio
async def test_blocked_email_delete_returns_not_found_for_unknown_id(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    response = await client.delete(f"/api/doctors/blocked/delete/{uuid4()}", headers=auth_headers(doctor))
    assert response.status_code == 404


@pytest.mark.anyio
async def test_doctor_cannot_delete_another_doctors_block(client: AsyncClient, db_session: AsyncSession):
    owner = await make_user(db_session, role="DOCTOR")
    other_doctor = await make_user(db_session, role="DOCTOR")
    created = await client.post(
        "/api/doctors/blocked/create",
        headers=auth_headers(owner),
        json={"email": "owned@example.com", "name": "Patient", "reason": None},
    )

    response = await client.delete(
        f"/api/doctors/blocked/delete/{created.json()['id']}", headers=auth_headers(other_doctor)
    )
    assert response.status_code == 403
