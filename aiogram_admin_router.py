import os
from dotenv import load_dotenv

from aiogram import Bot, Router, types
from aiogram.filters import Command

from db import get_info_user

load_dotenv('.env')

TG_API = os.getenv('TG_API')

bot = Bot(token=TG_API)

admin_router = Router()

@admin_router.message(Command('profile'))
async def send_info_user_message(message: types.Message):
	try:
		id_from_db = int(message.text.split()[1])

		info = get_info_user(id_from_db)
	except (IndexError, ValueError, TypeError) as _ex:
		# отвечаем, если админ не использовал пробел
		# или не ввёл <id>
		if isinstance(_ex, IndexError):
			await bot.send_message(message.chat.id,
				"""<p>Используйте /profile так:</p>
				   <p>/profile |id|</p>
				   <p>Повторите попытку</p>""", parse_mode='HTML')

		# отвечаем, если админ ввёл некорректный
		# или несуществующий <id>
		elif isinstance(_ex, ValueError) or isinstance(_ex, TypeError):
			await bot.send_message(message.chat.id,
				"""<p>Вы ввели некорректный или несуществующий |id|</p>
				   <p>|id| может состоять только из цифр</p>
				   <p>Повторите попытку</p>""", parse_mode='HTML')
	else:
		name = info['name']
		id_ = info['id']
		age = info['age']
		course = info['course']
		date_enrollment = info['date_enrollment']
		habitation = 'ДА' if info['habitation'] else 'НЕТ'

		balance = info['balance']
		if balance >= 0:
			balance_info = f'оплаченный период: {balance} дней'
		else:
			balance_info = f'просроченный период: {balance} дней'

		comment = info['comment']
		alarm_detail = '' if info['alarm_detail'] is None else info['alarm_detail']
		parent_id = info['parent_id']

		await bot.send_message(message.chat.id,
			f"""
				<p>
					{name}, id {id_}, {age} лет, {course} класс, дата зачисления: {date_enrollment},
					проживание: {habitation}, {balance_info}, справочная информация {comment},
					{alarm_detail} 
				</p>
				<p>
					<a href='https://t.me/{parent_id}'>Tg родителя: {parent_id}</a> 
				</p>
			""", parse_mode='HTML')
