import os
from dotenv import load_dotenv

from aiogram import Bot, Router, types, F
from aiogram.filters import Command 
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.input_file import InputFile

from generation_qr_code import generate_qr_code_and_get_path
from db import save_telegram_user_id_and_get_name, get_type_telegram_user,
			   get_balance, get_list_with_tuples_with_names_and_balances

load_dotenv('.env')

TG_API = os.getenv('TG_API')

bot = Bot(token=TG_API)

user_router = Router()

@user_router.message(Command(commands=['start', 'help']))
async def send_welcome_message(message: types.Message):
	await bot.send_message(message.chat.id, "Здравствуйте, я бот")


@user_router.message(Command('link_parent'))
async def save_tg_parent_id_to_db_and_send_message_about_it(message: types.Message):
	"""Сохраняет в базу parent_id родителя ребёнка по id в базе
	   и отправляет в чат сообщение об этом"""
	try:
		id_from_db = int(message.text.split()[1])

		name = save_telegram_user_id_and_get_name(
			id_=id_from_db, telegram_id=message.chat.id, type_user='parent')

	except (IndexError, ValueError, TypeError) as _ex:
		# отвечаем, если пользователь не использовал пробел
		# или не ввёл <id>
		if isinstance(_ex, IndexError):
			await bot.send_message(message.chat.id,
				"""Используйте /link_parent так:\n/link_parent <id>\n
				Повторите попытку""")

		# отвечаем, если пользователь ввёл некорректный,
		# несуществующий или чужой <id>
		elif isinstance(_ex, ValueError) or isinstance(_ex, TypeError):
			await bot.send_message(message.chat.id,
				"""Вы ввели некорректный или несуществующий <id>\n
				<id> может состоять только из цифр\n
				Повторите попытку""")
	else:
		await bot.send_message(message.chat.id, f'Вы записаны родителем ребёнка: {name}')


@user_router.message(Command('link_child'))
async def save_tg_child_id_to_db_and_send_message_about_it(message: types.Message):
	"""Сохраняет в базу child_id ребёнка по id в базе
	   и отправляет в чат сообщение об этом"""
	try:
		id_from_db = int(message.text.split()[1])

		name = save_telegram_user_id_and_get_name(
			id_=id_from_db, telegram_id=message.chat.id, type_user='child')
		
	except (IndexError, ValueError, TypeError) as _ex:
		# отвечаем, если пользователь не использовал пробел
		# или не ввёл <id>
		if isinstance(_ex, IndexError):
			await bot.send_message(message.chat.id,
				"""Используйте /link_child так:\n/link_child <id>\n
				Повторите попытку""")

		# отвечаем, если пользователь ввёл некорректный,
		# несуществующий или чужой <id>
		elif isinstance(_ex, ValueError) or isinstance(_ex, TypeError):
			await bot.send_message(message.chat.id,
				"""Вы ввели некорректный или несуществующий <id>\n
				<id> может состоять только из цифр\n
				Повторите попытку""")
	else:
		await bot.send_message(message.chat.id, f'{name}, вы записаны нашим учеником')


@user_router.message(Command('balance'))
async def send_message_with_qr_code_and_balance(message: types.Message):
	"""Если пользователь родитель, то выводит имена и баланс всех его детей,
	   если пользователь ребёнок, то выводит его баланс 
	   и сгенерированный QR-code для пополнения"""
	type_user = get_type_telegram_user(message.chat.id)

	if type_user is None:
		await bot.send_message(message.chat.id,
			"""Вы ещё не записаны родителем или ребёнком
			в нашей школе\nДля того, чтобы это сделать,
			воспользуйтесь одной из команд:\n
			/link_parent\n/link_child""")

	elif type_user == 'parent':
		names_and_balances = get_list_with_tuples_with_names_and_balances(message.chat.id)

		message_lines = list(map(lambda x: f'{x[0]}: {x[1]}', names_and_balances))

		message = '\n'.join(message_lines)

		await bot.send_message(message.chat.id, message)

	elif type_user == 'child':
		balance = get_balance(message.chat.id)

		qr_photo_path = generate_qr_code_and_get_path()
		qr_photo_file = InputFile(photo_path)

		await bot.send_photo(message.chat.id, qr_photo_file, caption=f'{balance}')


@user_router.message(F.content_type.in_({'photo', 'document'}))
async def send_thanks_message_for_payment_and_forward_receipt(message: types.Message):
	"""Отправляет сообщение-благодарность за оплату и
	   пересылает квитанцию в чат квитанций"""
	await bot.send_message(message.chat.id, 'Благодарим вас за оплату')

	# переслать квитанцию в чат квитанций