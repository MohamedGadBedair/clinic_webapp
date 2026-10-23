import os
from collections.abc import AsyncGenerator

import sys
from pathlib import Path


import asyncio
import pytest

# التصحيح (إضافة word '_loop'):
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from httpx2 import ASGITransport,AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine 
from sqlalchemy.pool import NullPool

from main import app
from database import Base, get_db

# 
os.environ['SECRET_KEY'] = ('8995314cc07839e08179a21841ff8775c34eb94c8d9f2ee6f1b122cfc4d71ae2')

os.environ['DB_URL'] = ('postgresql+psycopg://postgres:1234@localhost:5432/test_clienc')

database_url= os.environ['DB_URL']
AUTH_PREFIX = '/api/authentication'

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


