from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.api_helpers import auth_headers, make_user


@pytest.mark.anyio
async def test_client_can_read_an_empty_conversation_list(client: AsyncClient, db_session: AsyncSession):
    patient = await make_user(db_session, role="CLIENT")

    response = await client.get("/api/chats", headers=auth_headers(patient))

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_chat_conversation_list_requires_authentication(client: AsyncClient):
    assert (await client.get("/api/chats")).status_code == 401


@pytest.mark.anyio
async def test_websocket_reports_invalid_json_before_disconnect():
    """Exercise the WebSocket endpoint's protocol error response without a network server."""
    from Routers.chat import websocket_chat_endpoint

    websocket = AsyncMock()
    websocket.receive_text.side_effect = ["not-json", RuntimeError("connection closed")]
    current_user = object()
    db = AsyncMock()

    with patch("Routers.chat.get_current_user", new=AsyncMock(return_value=current_user)), patch(
        "Routers.chat.get_user_conection_list", new=AsyncMock(return_value=[])
    ), patch("Routers.chat.manager.connect", new=AsyncMock()), patch(
        "Routers.chat.manager.disconnect", new=AsyncMock()
    ) as disconnect:
        await websocket_chat_endpoint(websocket, "token", db)

    assert websocket.send_json.await_args_list[0].args[0] == {"message": "hello"}
    assert websocket.send_json.await_args_list[1].args[0] == {"error": "Invalid JSON format"}
    disconnect.assert_awaited_once_with(current_user, db)
