from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import hashed_secret_token, verify_password
from models import DoctorClient, PasswordResetToken, User, ValidateEmailToken

AUTH_PREFIX = '/api/authentication'


def _register_payload(
    username: str = 'testdoctor',
    email: str = 'doctor@example.com',
    password: str = 'testpassword123',
    role: str = 'doctor',
    doctor_id=None,
) -> dict:
    return {
        'username': username,
        'email': email,
        'password': password,
        'role': role,
        'doctor_id': doctor_id,
    }

async def register_user(client: AsyncClient, **kwargs):
    with patch(
        'Routers.authentication.send_email_handler',
        new_callable=AsyncMock,
    ):
        return await client.post(f'{AUTH_PREFIX}/', json=_register_payload(**kwargs))

async def get_user_by_email(db_session: AsyncSession, email: str) -> User:
    result = await db_session.execute(
        select(User).where(User.email == email.strip().lower())
    )
    user = result.scalars().first()
    assert user is not None
    return user

async def add_validate_email_token(
    db_session: AsyncSession,
    user_id,
    raw_token: str,
    expires_at: datetime | None = None,
) -> str:
    token_row = ValidateEmailToken(
        user_id=user_id,
        token_hash=hashed_secret_token(raw_token),
        expires_at=expires_at
        or (datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)),
    )
    db_session.add(token_row)
    await db_session.commit()
    return raw_token

async def add_reset_password_token(
    db_session: AsyncSession,
    user_id,
    raw_token: str,
    expires_at: datetime | None = None,
) -> str:
    token_row = PasswordResetToken(
        user_id=user_id,
        token_hash=hashed_secret_token(raw_token),
        expires_at=expires_at
        or (datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)),
    )
    db_session.add(token_row)
    await db_session.commit()
    return raw_token

async def register_and_validate_doctor(
    client: AsyncClient,
    db_session: AsyncSession,
    username: str = 'testdoctor',
    email: str = 'doctor@example.com',
    password: str = 'testpassword123',
) -> User:
    response = await register_user(
        client,
        username=username,
        email=email,
        password=password,
        role='doctor',
        doctor_id=None,
    )
    assert response.status_code == 201, response.text
    user = await get_user_by_email(db_session, email)
    user.validated = True
    await db_session.commit()
    return user

# ===================={Test Register AS Doctor}====================================
@pytest.mark.anyio
async def test_register_doctor_success(
    client: AsyncClient,
    db_session: AsyncSession
    ):

    with patch(
        'Routers.authentication.send_email_handler',
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            f'{AUTH_PREFIX}/',
            json=_register_payload(),
        )

    assert response.status_code == 201
    assert response.json()['message'] == (
        'check your email, you will recive vialidation instructions.'
    )
    mock_send.assert_called_once()

    user = await get_user_by_email(db_session, 'doctor@example.com')
    assert user.username == 'testdoctor'
    assert user.validated is False
    assert user.password_hash is not None
    assert 'password' not in response.json()
    assert 'password_hash' not in response.json()


@pytest.mark.anyio
async def test_register_normalizes_username_and_email(
    client: AsyncClient,
    db_session: AsyncSession,
):
    response = await register_user(
        client,
        username='  TestDoctor  ',
        email='  Doctor@Example.COM  ',
        role='doctor',
        doctor_id=None,
    )
    assert response.status_code == 201
    user = await get_user_by_email(db_session, 'doctor@example.com')
    assert user.username == 'testdoctor'
    assert user.email == 'doctor@example.com'

#====================================={test}
@pytest.mark.anyio
async def test_register_client_success(client: AsyncClient, db_session: AsyncSession):
    doctor = await register_and_validate_doctor(client, db_session)
    # register looks up doctors with role == 'DOCTOR'
    doctor.role = 'DOCTOR'
    await db_session.commit()

    response = await register_user(
        client,
        username='testclient',
        email='client@example.com',
        password='testpassword123',
        role='client',
        doctor_id=str(doctor.id),
    )
    assert response.status_code == 201, response.text

    client_user = await get_user_by_email(db_session, 'client@example.com')
    link_q = await db_session.execute(
        select(DoctorClient).where(
            DoctorClient.doctor_id == doctor.id,
            DoctorClient.client_id == client_user.id,
        )
    )
    assert link_q.scalars().first() is not None


@pytest.mark.anyio
async def test_register_client_requires_doctor_id(client: AsyncClient):
    response = await register_user(
        client,
        username='testclient',
        email='client@example.com',
        role='client',
        doctor_id=None,
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'doctor_id is required for clients'


@pytest.mark.anyio
async def test_register_client_invalid_doctor_id(client: AsyncClient):
    response = await register_user(
        client,
        username='testclient',
        email='client@example.com',
        role='client',
        doctor_id=str(uuid4()),
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'doctor_id is invalid'


@pytest.mark.anyio
async def test_register_client_rejects_non_doctor_as_doctor_id(
    client: AsyncClient,
    db_session: AsyncSession,
):
    first_doctor = await register_and_validate_doctor(client, db_session)
    first_doctor.role = 'DOCTOR'
    await db_session.commit()

    other_client = await register_user(
        client,
        username='otherclient',
        email='otherclient@example.com',
        role='client',
        doctor_id=str(first_doctor.id),
    )
    assert other_client.status_code == 201
    other = await get_user_by_email(db_session, 'otherclient@example.com')

    response = await register_user(
        client,
        username='newclient',
        email='newclient@example.com',
        role='client',
        doctor_id=str(other.id),
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'doctor_id is invalid'


@pytest.mark.anyio
async def test_register_duplicate_username(client: AsyncClient):
    first = await register_user(client)
    assert first.status_code == 201
    response = await register_user(
        client,
        username='testdoctor',
        email='other@example.com',
        role='doctor',
        doctor_id=None,
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'this user already exist'


@pytest.mark.anyio
async def test_register_duplicate_username_case_insensitive(client: AsyncClient):
    first = await register_user(client, username='TestDoctor')
    assert first.status_code == 201
    response = await register_user(
        client,
        username='testdoctor',
        email='other@example.com',
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'this user already exist'


@pytest.mark.anyio
async def test_register_duplicate_email(client: AsyncClient):
    first = await register_user(client)
    assert first.status_code == 201
    response = await register_user(
        client,
        username='anotheruser',
        email='doctor@example.com',
        role='doctor',
        doctor_id=None,
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'this user already exist'


@pytest.mark.anyio
async def test_register_duplicate_email_case_insensitive(client: AsyncClient):
    first = await register_user(client)
    assert first.status_code == 201
    response = await register_user(
        client,
        username='anotheruser',
        email='Doctor@Example.com',
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'this user already exist'


@pytest.mark.anyio
async def test_register_validation_errors(client: AsyncClient):
    response = await client.post(f'{AUTH_PREFIX}/')
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'

    response = await client.post(f'{AUTH_PREFIX}/', json={})
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/',
        json={'username': 't', 'email': 'bad', 'password': 'short', 'role': 'nurse'},
    )
    assert response.status_code == 422


# ===================={Test Validate Email}====================================
@pytest.mark.anyio
async def test_validate_email_success(client: AsyncClient, db_session: AsyncSession):
    register = await register_user(client)
    assert register.status_code == 201
    user = await get_user_by_email(db_session, 'doctor@example.com')
    assert user.validated is False

    raw_token = await add_validate_email_token(db_session, user.id, 'valid-email-token')
    response = await client.get(f'{AUTH_PREFIX}/vialidate_email/{raw_token}')
    assert response.status_code == 200
    assert response.json()['message'] == (
        'Email validated successfully. you can log in with your email.'
    )

    await db_session.refresh(user)
    assert user.validated is True
    leftover = await db_session.execute(
        select(ValidateEmailToken).where(ValidateEmailToken.user_id == user.id)
    )
    assert leftover.scalars().first() is None


@pytest.mark.anyio
async def test_validate_email_invalid_token(client: AsyncClient):
    response = await client.get(f'{AUTH_PREFIX}/vialidate_email/not-a-real-token')
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired token'


@pytest.mark.anyio
async def test_validate_email_expired_token(
    client: AsyncClient,
    db_session: AsyncSession,
):
    register = await register_user(client)
    assert register.status_code == 201
    user = await get_user_by_email(db_session, 'doctor@example.com')
    raw_token = await add_validate_email_token(
        db_session,
        user.id,
        'expired-email-token',
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    response = await client.get(f'{AUTH_PREFIX}/vialidate_email/{raw_token}')
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired token'


@pytest.mark.anyio
async def test_validate_email_user_missing(
    client: AsyncClient,
    db_session: AsyncSession,
):
    token_row = ValidateEmailToken(
        user_id=uuid4(),
        token_hash=hashed_secret_token('orphan-token'),
        expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
    )
    db_session.add(token_row)
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        pytest.skip('user_id foreign key prevents orphan validation tokens')

    response = await client.get(f'{AUTH_PREFIX}/vialidate_email/orphan-token')
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired token'


# ===================={Test Login}====================================
@pytest.mark.anyio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    await register_and_validate_doctor(client, db_session)
    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com', 'password': 'testpassword123'},
    )
    assert response.status_code == 200
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'


@pytest.mark.anyio
async def test_login_email_case_insensitive(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await register_and_validate_doctor(client, db_session)
    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'Doctor@Example.COM', 'password': 'testpassword123'},
    )
    assert response.status_code == 200
    assert 'access_token' in response.json()


@pytest.mark.anyio
async def test_login_unvalidated_email(client: AsyncClient):
    register = await register_user(client)
    assert register.status_code == 201
    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com', 'password': 'testpassword123'},
    )
    assert response.status_code == 401
    assert response.json()['detail'] == (
        'Email not validated. Please vialidate your email first.'
    )


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    await register_and_validate_doctor(client, db_session)
    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com', 'password': 'wrongpassword'},
    )
    assert response.status_code == 401
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.anyio
async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'missing@example.com', 'password': 'testpassword123'},
    )
    assert response.status_code == 401
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.anyio
async def test_login_validation_errors(client: AsyncClient):
    response = await client.post(f'{AUTH_PREFIX}/login')
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'

    response = await client.post(f'{AUTH_PREFIX}/login', data={})
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com'},
    )
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'password': 'testpassword123'},
    )
    assert response.status_code == 422


# ===================={Test Forgot Password}====================================
@pytest.mark.anyio
async def test_forgot_password_success(client: AsyncClient):
    register = await register_user(client)
    assert register.status_code == 201
    with patch(
        'Routers.authentication.send_email_handler',
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            f'{AUTH_PREFIX}/forgot_password',
            json={'email': 'doctor@example.com'},
        )
    assert response.status_code == 202
    assert response.json()['message'] == (
        'if an account exists with this email, you will recive password reset instructions.'
    )
    mock_send.assert_called_once()


@pytest.mark.anyio
async def test_forgot_password_email_case_insensitive(client: AsyncClient):
    register = await register_user(client)
    assert register.status_code == 201
    with patch(
        'Routers.authentication.send_email_handler',
        new_callable=AsyncMock,
    ) as mock_send:
        response = await client.post(
            f'{AUTH_PREFIX}/forgot_password',
            json={'email': '  Doctor@Example.COM  '},
        )
    assert response.status_code == 202
    mock_send.assert_called_once()


@pytest.mark.anyio
async def test_forgot_password_invalid_email(client: AsyncClient):
    response = await client.post(
        f'{AUTH_PREFIX}/forgot_password',
        json={'email': 'missing@example.com'},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid email'


@pytest.mark.anyio
async def test_forgot_password_validation_errors(client: AsyncClient):
    response = await client.post(f'{AUTH_PREFIX}/forgot_password')
    assert response.status_code == 422

    response = await client.post(f'{AUTH_PREFIX}/forgot_password', json={})
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/forgot_password',
        json={'email': 'not-an-email'},
    )
    assert response.status_code == 422


# ===================={Test Reset Password}====================================
@pytest.mark.anyio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession):
    user = await register_and_validate_doctor(client, db_session)
    raw_token = await add_reset_password_token(db_session, user.id, 'valid-reset-token')

    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'token': raw_token, 'new_password': 'newpassword123'},
    )
    assert response.status_code == 200
    assert response.json()['message'] == (
        'password reset successfully. you can log in with your new password.'
    )

    leftover = await db_session.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    assert leftover.scalars().first() is None

    await db_session.refresh(user)
    assert verify_password('newpassword123', user.password_hash)
    assert not verify_password('testpassword123', user.password_hash)

    old_login = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com', 'password': 'testpassword123'},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        f'{AUTH_PREFIX}/login',
        data={'username': 'doctor@example.com', 'password': 'newpassword123'},
    )
    assert new_login.status_code == 200
    assert 'access_token' in new_login.json()
    assert new_login.json()['token_type'] == 'bearer'


@pytest.mark.anyio
async def test_reset_password_invalid_token(client: AsyncClient):
    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'token': 'not-a-real-token', 'new_password': 'newpassword123'},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired token'


@pytest.mark.anyio
async def test_reset_password_expired_token(
    client: AsyncClient,
    db_session: AsyncSession,
):
    user = await register_and_validate_doctor(client, db_session)
    raw_token = await add_reset_password_token(
        db_session,
        user.id,
        'expired-reset-token',
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
    )
    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'token': raw_token, 'new_password': 'newpassword123'},
    )
    assert response.status_code == 400
    assert response.json()['detail'] == 'Invalid or expired token'


@pytest.mark.anyio
async def test_reset_password_validation_errors(client: AsyncClient):
    response = await client.post(f'{AUTH_PREFIX}/reset_password')
    assert response.status_code == 422

    response = await client.post(f'{AUTH_PREFIX}/reset_password', json={})
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'token': 'some-token'},
    )
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'new_password': 'newpassword123'},
    )
    assert response.status_code == 422

    response = await client.post(
        f'{AUTH_PREFIX}/reset_password',
        json={'token': 'some-token', 'new_password': 'short'},
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == (
        'String should have at least 8 characters'
    )
