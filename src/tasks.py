from celery import Celery
from celery.schedules import crontab
import celery

from models import User, Subscribes

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from os import getenv
from dotenv import load_dotenv

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import aiohttp
import asyncio


load_dotenv()
TOKEN = getenv("BOT_TOKEN")
RATE_URL = getenv("RATE_URL")

app = Celery('tasks', broker='pyamqp://guest@localhost//')

engine = create_async_engine(
    "postgresql+asyncpg://forms_admin:qwerty@localhost/telegram_bot")
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def bot_notify():
    """Get users with subscribes and send notifications to them"""
    async with async_session() as session:
        stmt = select(User).options(selectinload(User.subscribes)
                                    ).where(Subscribes.code == 'rate')
        users = await session.execute(stmt)
        async with aiohttp.ClientSession() as request_session:
            async with request_session.get(RATE_URL) as response:
                json = await response.json()
                conversion_rate = f'1/{json["conversion_rates"]["RUB"]}'
        for user in users.scalars():
            async with Bot(
                token=TOKEN,
                default=DefaultBotProperties(
                    parse_mode=ParseMode.HTML,
                ),
            ) as bot:
                await bot.send_message(chat_id=user.chat_id, text=conversion_rate)


@app.task
def run_notify():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot_notify())


app.conf.beat_schedule = {
    'add-every-30-seconds': {
        'task': 'tasks.run_notify',
        'schedule': crontab(minute='*/15'),
    },
}
app.conf.timezone = 'UTC'
