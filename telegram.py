import os
import logging
from dotenv import load_dotenv

import asyncio
from aiogram import Bot, Dispatcher

from aiogram_router_commands import commands_router
#from aiogram_router_buttons import buttons_router

load_dotenv('.env')

TG_API = os.getenv('TG_API')

async def bot_config():
	global TG_API

	bot = Bot(token=TG_API)

	dp = Dispatcher()
	dp.include_routers(commands_router)

	await dp.start_polling(bot)

def start_bot():
	logging.basicConfig(level=logging.INFO)
	asyncio.run(bot_config())
