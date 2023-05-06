import os
import logging
from dotenv import load_dotenv

import asyncio
from aiogram import Bot, Dispatcher

from aiogram_user_router import user_router
from aiogram_admin_router import admin_router

load_dotenv('.env')

TG_API = os.getenv('TG_API')

async def bot_config():
	global TG_API

	bot = Bot(token=TG_API)

	dp = Dispatcher()
	dp.include_routers(admin_router)

	await dp.start_polling(bot)

def start_bot():
	logging.basicConfig(level=logging.INFO)
	asyncio.run(bot_config())
