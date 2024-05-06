import asyncio
import logging
import sys
from os import getenv
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import User, History, Subscribes
import datetime
import aiohttp


load_dotenv()
TOKEN = getenv("BOT_TOKEN")
RATE_URL = getenv("RATE_URL")

dp = Dispatcher()

engine = create_async_engine(
    "postgresql+asyncpg://postgres:postgres@db/postgres")
async_session = async_sessionmaker(engine, expire_on_commit=False)

RATE = 'rate'


async def get_user(id, session):
    """Get and return user row from database"""
    try:
        stmt = select(User).where(User.user_id == str(id))
        user_instance = await session.execute(stmt)
        user_instance = user_instance.scalars().one()
        return user_instance
    except Exception as e:
        return None


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Create new user if doesn't exist and say hello"""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(message.from_user.id, session)
            if user is not None:
                user.chat_id = str(message.chat.id)
                await session.commit()
            else:
                session.add(User(user_id=str(message.from_user.id),
                                 username=message.from_user.username,
                                 chat_id=str(message.chat.id)))
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}!" +
                         "Чтобы воспользоваться справкой выполните команду /help")


@dp.message(Command(commands=['rate']))
async def command_rate_handler(message: Message) -> None:
    """Get and return rate"""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(message.from_user.id, session)
            async with aiohttp.ClientSession() as request_session:
                async with request_session.get(RATE_URL) as response:
                    json = await response.json()
                    conversion_rate = json["conversion_rates"]["RUB"]
            history = History(request_date=datetime.datetime.now(),
                              rate=f'1/{conversion_rate}', user_id=user.id)
            session.add(history)
    await message.answer(f"{history.rate}")


@dp.message(Command(commands=['history']))
async def command_history_handler(message: Message) -> None:
    """Return history"""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(message.from_user.id, session)
            try:
                stmt = select(History).where(
                    History.user_id == user.id).order_by(History.id)
                history = await session.execute(stmt)
            except Exception as e:
                history = None
            if history is not None:
                text = ''
                for row in history.scalars():
                    text += f"{row.request_date}: {row.rate}\n"
            else:
                text = 'История пуста'
    await message.answer(text)


@dp.message(Command(commands=['subscribe']))
async def command_subscribe_handler(message: Message) -> None:
    """Subscribe user for rate info"""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(message.from_user.id, session)
            try:
                stmt = select(Subscribes).where(Subscribes.user_id == user.id,
                                                Subscribes.code == RATE)
                subscribe_instance = await session.execute(stmt)
                subscribe_instance = subscribe_instance.scalars().one()
            except Exception as e:
                subscribe_instance = None
            if subscribe_instance is not None:
                subscribe = subscribe_instance
            else:
                subscribe = Subscribes(code=RATE, user_id=user.id)
                session.add(subscribe)
    await message.answer("Вы подписаны на переодическое получение информации о курсе usdrub")


@dp.message(Command(commands=['unsubscribe']))
async def command_unsubscribe_handler(message: Message) -> None:
    """Unsubscribe user"""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(message.from_user.id, session)
            try:
                stmt = select(Subscribes).where(Subscribes.user_id == user.id,
                                                Subscribes.code == RATE)
                subscribe_instance = await session.execute(stmt)
                subscribe_instance = subscribe_instance.scalars().one()
            except Exception as e:
                subscribe_instance = None
            if subscribe_instance is not None:
                await session.delete(subscribe_instance)
    await message.answer("Подписка удалена")


@dp.message(Command(commands=['help']))
async def command_unsubscribe_handler(message: Message) -> None:
    text = '1) Чтобы получить данные о текущем курсе usd/rub выполните команду /rate.\n' + \
           '2) Чтобы просмотреть историю просмотра данных о курсе выполните команду /history.\n' + \
           '3) Чтобы подписаться на переодические уведомления о состоянии текущего курса usd/rub' + \
           'выполните команду /subscribe.\n' + \
           '4) Чтобы удалить подписку выполните команду /unsubscribe.\n' + \
           '5) Чтобы воспользоваться справкой выполните команду /help'
    await message.answer(text)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
