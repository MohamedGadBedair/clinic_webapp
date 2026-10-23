import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_payment_endpoint_is_registered(client: AsyncClient):
    """The payment intent endpoint requires an authenticated caller."""
    response = await client.post("/api/payment", params={"appointment_id": "not-an-id"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_payment_webhook_requires_a_payload(client: AsyncClient):
    response = await client.post("/api/payment/webhook")
    assert response.status_code == 422
