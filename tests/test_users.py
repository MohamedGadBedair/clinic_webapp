from unittest.mock import patch

import pytest
from httpx import AsyncClient
from PIL import UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from auth import verify_password
from tests.api_helpers import auth_headers, make_user


USER_PREFIX = "/api/users"
VALID_PHONE = "20123456789"


@pytest.mark.anyio
async def test_me_returns_the_authenticated_user(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")

    response = await client.get(f"{USER_PREFIX}/me", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert "password_hash" not in response.json()


@pytest.mark.anyio
async def test_me_requires_authentication(client: AsyncClient):
    response = await client.get(f"{USER_PREFIX}/me")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_user_changes_profile_fields(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")

    response = await client.patch(
        f"{USER_PREFIX}/",
        headers=auth_headers(user),
        json={
            "username": "updated-user",
            "email": "UPDATED@example.com",
            "phone": VALID_PHONE,
            "city": "Cairo",
            "gender": "male",
            "description": "Patient profile",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["username"] == "updated-user"
    assert body["email"] == "updated@example.com"
    assert body["city"] == "CAIRO"
    assert body["phone"] == VALID_PHONE


@pytest.mark.anyio
async def test_update_user_rejects_duplicate_username_and_email(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")
    existing = await make_user(db_session, role="CLIENT")
    headers = auth_headers(user)

    username_response = await client.patch(
        f"{USER_PREFIX}/", headers=headers, json={"username": existing.username, "phone": VALID_PHONE}
    )
    email_response = await client.patch(
        f"{USER_PREFIX}/", headers=headers, json={"email": existing.email, "phone": VALID_PHONE}
    )

    assert username_response.status_code == 400
    assert email_response.status_code == 400


@pytest.mark.anyio
async def test_update_user_requires_authentication_and_valid_phone(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")

    unauthorized = await client.patch(f"{USER_PREFIX}/", json={"phone": VALID_PHONE})
    invalid = await client.patch(f"{USER_PREFIX}/", headers=auth_headers(user), json={"phone": "short"})

    assert unauthorized.status_code == 401
    assert invalid.status_code == 422


@pytest.mark.anyio
async def test_change_password_updates_stored_hash(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")

    response = await client.post(
        f"{USER_PREFIX}/me/password",
        headers=auth_headers(user),
        json={"current_password": "password123", "new_password": "newpassword123"},
    )

    assert response.status_code == 200
    await db_session.refresh(user)
    assert verify_password("newpassword123", user.password_hash)


@pytest.mark.anyio
async def test_change_password_rejects_bad_or_invalid_input(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")
    headers = auth_headers(user)

    bad_current = await client.post(
        f"{USER_PREFIX}/me/password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "newpassword123"},
    )
    short_new = await client.post(
        f"{USER_PREFIX}/me/password",
        headers=headers,
        json={"current_password": "password123", "new_password": "short"},
    )
    unauthorized = await client.post(
        f"{USER_PREFIX}/me/password",
        json={"current_password": "password123", "new_password": "newpassword123"},
    )

    assert bad_current.status_code == 400
    assert short_new.status_code == 422
    assert unauthorized.status_code == 401


@pytest.mark.anyio
async def test_upload_replaces_and_deletes_profile_picture(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")
    headers = auth_headers(user)
    with patch("Routers.user.process_profile_imge", return_value="new-avatar.webp"), patch(
        "Routers.user.delete_profile_image"
    ) as delete_image:
        upload = await client.post(
            f"{USER_PREFIX}/picture",
            headers=headers,
            files={"file": ("avatar.webp", b"image-bytes", "image/webp")},
        )
        deleted = await client.delete(f"{USER_PREFIX}/picture", headers=headers)

    assert upload.status_code == 202
    assert upload.json()["user_profile_img"] == "new-avatar.webp"
    assert deleted.status_code == 204
    delete_image.assert_called_once_with("new-avatar.webp")


@pytest.mark.anyio
async def test_upload_profile_picture_rejects_invalid_image(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")
    with patch("Routers.user.process_profile_imge", side_effect=UnidentifiedImageError("invalid image")):
        response = await client.post(
            f"{USER_PREFIX}/picture",
            headers=auth_headers(user),
            files={"file": ("not-image.txt", b"not an image", "text/plain")},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image. please upload a valid imge (JPEG,PNG,GIF,WebP)"


@pytest.mark.anyio
async def test_profile_picture_endpoints_validate_file_and_existing_picture(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")
    headers = auth_headers(user)

    missing_file = await client.post(f"{USER_PREFIX}/picture", headers=headers)
    no_picture = await client.delete(f"{USER_PREFIX}/picture", headers=headers)
    unauthorized = await client.post(
        f"{USER_PREFIX}/picture", files={"file": ("avatar.png", b"image", "image/png")}
    )

    assert missing_file.status_code == 422
    assert no_picture.status_code == 400
    assert unauthorized.status_code == 401


@pytest.mark.anyio
async def test_delete_user_requires_confirmation_and_authentication(client: AsyncClient, db_session: AsyncSession):
    user = await make_user(db_session, role="CLIENT")

    invalid_confirmation = await client.request(
        "DELETE",
        f"{USER_PREFIX}/",
        headers=auth_headers(user),
        json={"confirm": "keep account", "confirm_password": "password123"},
    )
    missing_body = await client.request("DELETE", f"{USER_PREFIX}/", headers=auth_headers(user))
    unauthorized = await client.request(
        "DELETE", f"{USER_PREFIX}/", json={"confirm": "DELETE_MY_ACCOUNT", "confirm_password": "password123"}
    )

    assert invalid_confirmation.status_code == 400
    assert missing_body.status_code == 422
    assert unauthorized.status_code == 401
