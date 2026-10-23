import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api_helpers import auth_headers, make_user


@pytest.mark.anyio
async def test_client_dashboard_returns_an_empty_summary(client: AsyncClient, db_session: AsyncSession):
    patient = await make_user(db_session, role="CLIENT")

    response = await client.get("/api/dashboard/dashboard", headers=auth_headers(patient))

    assert response.status_code == 200, response.text
    assert response.json()["total_appointments"] == 0
    assert response.json()["files"] == []
    assert response.json()["total_New_files"] is None


@pytest.mark.anyio
async def test_dashboard_requires_authentication(client: AsyncClient):
    assert (await client.get("/api/dashboard/dashboard")).status_code == 401
