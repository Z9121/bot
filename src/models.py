from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import (DeclarativeBase, Mapped,
                            mapped_column, selectinload,
                            relationship)
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, AsyncSession
from sqlalchemy import ForeignKey
import datetime
import asyncio
from typing import List


class Base(AsyncAttrs, DeclarativeBase):
    pass


class History(Base):
    __tablename__ = "history"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_date: Mapped[datetime.datetime] = mapped_column(nullable=True)
    rate: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)


class Subscribes(Base):
    __tablename__ = "subscribes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str]
    description: Mapped[str] = mapped_column(nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str]
    username: Mapped[str]
    chat_id: Mapped[str]
    subscribes: Mapped[List[Subscribes]] = relationship()
    history: Mapped[List[History]] = relationship()


async def main() -> None:
    engine = create_async_engine("postgresql+asyncpg://postgres:postgres@db/postgres")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

if __name__ == '__main__':
    asyncio.run(main())
