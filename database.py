import uuid
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker,create_async_engine

from config import settings

database_url= settings.db_url

engine=create_async_engine(database_url)

AsyncSessionLocal=async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
    )
class Base(DeclarativeBase):
    id :Mapped[uuid.UUID]=mapped_column(default=uuid.uuid1,primary_key=True,index=True)
    pass

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db 
