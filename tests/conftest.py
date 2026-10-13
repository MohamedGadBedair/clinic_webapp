import os
from collections.abc import AsyncGenerator

import sys
from pathlib import Path
import asyncio

# root_dir = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(root_dir))

# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest


# os.environ['SECRET_KEY'] = ('8995314cc07839e08179a21841ff8775c34eb94c8d9f2ee6f1b122cfc4d71ae2')

os.environ['DB_NAME'] = ('postgresql+psycopg')
os.environ['DATABASE_USERNAME'] = ('postgres')
os.environ['DATABASE_PASSWORD'] = ('1234')
os.environ['DATABASE_HOSTNAME'] = ('localhost')
os.environ['DATABASE_PORT'] = ('5432')
os.environ['DATABASE_NAME'] = ('test_blog')
database_url= f'{os.environ['DB_NAME']}://{os.environ['DATABASE_USERNAME']}:{os.environ['DATABASE_PASSWORD']}@{os.environ['DATABASE_HOSTNAME']}:{os.environ['DATABASE_PORT']}/{os.environ['DATABASE_NAME']}'

import pytest
from httpx import ASGITransport,AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine 
from sqlalchemy.pool import NullPool

from main import app
from database import Base, get_db

@pytest.fixture(scope='session')
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope='session')
def test_engine():
    engin=create_async_engine(
        database_url,
        poolclass=NullPool
    )
    return engin

@pytest.fixture(scope='session')
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

@pytest.fixture
async def db_session(
    test_engine,
    setup_database
)->AsyncGenerator[AsyncSession]:
    
    conn = await test_engine.connect()
    trans = await conn.begin()

    test_async_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode='create_savepoint'
    )


    async with test_async_session() as session:
        try :
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()

@pytest.fixture
async def client(
    db_session:AsyncSession,
)->AsyncGenerator[AsyncClient]:
    
    async def overridw_get_db():
        yield db_session

    app.dependency_overrides[get_db]=overridw_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test'
    )as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_user(
        client:AsyncClient,
        username:str='testuser',
        email:str='test@example.com',
        password:str='testpassword123'
 )->dict:
    response=await client.post(
        '/api/users/',
        json={
            'username':username,
            'email':email,
            'password':password
        }
    )
    assert response.status_code == 201, f'faild to create user:{response.text}'
    return response.json()

async def login_user(
        client:AsyncClient,
        user_email='test@example.com',
        user_password='testpassword123'
)->dict:
    
    response=await client.post(
        '/api/users/token',data={
            'username':user_email,
            'password':user_password
        })
    assert response.status_code==200,f'failed to login:{response.text}'
    return response.json()

def auth_header(token:str)->dict[str,str]:
    return {'Authorization':f'{token["token_type"]} {token['access_token']}'}