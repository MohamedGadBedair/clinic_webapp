from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import MedicalFile
from tests.api_helpers import auth_headers, make_user


@pytest.mark.anyio
async def test_client_can_list_upload_and_delete_files(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    patient = await make_user(db_session, role="CLIENT")
    headers = auth_headers(patient)

    with patch("Routers.files.process_client_files", return_value="report.pdf"), patch("Routers.files.delete_client_file") as delete_file:
        uploaded = await client.post(
            "/api/clients/files/upload",
            headers=headers,
            data={"kind": "lab", "doctor_id": str(doctor.id)},
            files={"client_file": ("report.pdf", b"PDF", "application/pdf")},
        )
        assert uploaded.status_code == 201, uploaded.text
        file_id = uploaded.json()["id"]

        listed = await client.get("/api/clients/files/", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == file_id

        deleted = await client.delete(f"/api/clients/files/delete/{file_id}", headers=headers)

    assert deleted.status_code == 204
    delete_file.assert_called_once_with("report.pdf")


@pytest.mark.anyio
async def test_doctors_cannot_upload_client_files(client: AsyncClient, db_session: AsyncSession):
    doctor = await make_user(db_session, role="DOCTOR")
    response = await client.post(
        "/api/clients/files/upload",
        headers=auth_headers(doctor),
        data={"kind": "lab", "doctor_id": str(uuid4())},
        files={"client_file": ("report.pdf", b"PDF", "application/pdf")},
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_file_list_requires_authentication(client: AsyncClient):
    response = await client.get("/api/clients/files/")
    assert response.status_code == 401
