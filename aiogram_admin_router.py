import os
from dotenv import load_dotenv

from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from db import get_info_user, boost_and_get_balance, stop_account_and_get_name,
			   delete_user_and_get_name,

load_dotenv('.env')

TG_API = os.getenv('TG_API')

bot = Bot(token=TG_API)

admin_router = Router()

class MyCallback(CallbackData, prefix='my_callback'):
	id: int,
	foo: str


@admin_router.message(Command('profile'))
async def send_info_user_message(message: types.Message):
	"""Отправляет сообщение в чат с информацией о пользователе
	   и клавиатуру для взаимодействия с базой"""
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

		inline_builder = InlineKeyboardBuilder()

		inline_builder.button(text='Оплата произведена (+28 дней)', callback_data=MyCallback(
			id=id_, foo='inline_button_balance').pack())
		inline_builder.button(text='Приостановить счетчик ученика', callback_data=MyCallback(
			id=id_, foo='inline_button_pause').pack())
		inline_builder.button(text='ALARM', callback_data=MyCallback(
			id=id_, foo='inline_button_alarm').pack())
		inline_builder.button(text='Ученик выбыл', callback_data=MyCallback(
			id=id_, foo='inline_button_delete').pack())

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
			""", parse_mode='HTML', reply_markup=inline_builder.as_markup())


@admin_router.callback_query(MyCallback.filter(F.foo == 'inline_button_balance'))
async def boost_user_balance(query: types.CallbackQuery, callback_data: MyCallback):
	"""Добавляет к балансу ученика 28 дней"""
	id_from_db = callback_data.id

	new_balance = boost_and_get_balance(id_from_db)

	await bot.send_message(query.from_user.id, f'Новый баланс: {new_balance}')


@admin_router.callback_query(MyCallback.filter(F.foo == 'inline_button_pause'))
async def stop_account_user(query: types.CallbackQuery, callback_data: MyCallback):
	"""Приостанавливает счетчик ученика"""
	id_from_db = callback_data.id

	name = stop_account_and_get_name(id_from_db)

	await bot.send_message(query.from_user.id, f'Счётчик {name} приостановлен')


@admin_router.callback_query(MyCallback.filter(F.foo == 'inline_button_delete'))
async def request_validate_delete_user(query: types.CallbackQuery, callback_data: MyCallback):
	"""Запрашивает подтверждение на удаление ученика из базы"""
	id_from_db = callback_data.id

	inline_builder = InlineKeyboardBuilder()

	inline_builder.button(text='Подтвердить', callback_data=MyCallback(
		id=id_from_db, foo='inline_button_delete_validate').pack())
	inline_builder.button(text='Отмена', callback_data=MyCallback(
		id=id_from_db, foo='inline_button_delete_cancel'))

	await bot.send_message(query.from_user.id, 'Подтвердите удаление',
		reply_markup=inline_builder.as_markup())


@admin_router.callback_query(MyCallback.filter(F.foo == 'inline_button_delete_validate'))
async def delete_user(query: types.CallbackQuery, callback_data: MyCallback):
	id_from_db = callback_data.id

	name = delete_user_and_get_name(id_from_db)

	await bot.send_message(query.from_user.id, f'Ученик {name} удалён')


@admin_router.callback_query(MyCallback.filter(F.foo == 'inline_button_delete_cancel'))
async def delete_user(query: types.CallbackQuery, callback_data: MyCallback):
	await bot.send_message(query.from_user.id, f'Удаление отменено')