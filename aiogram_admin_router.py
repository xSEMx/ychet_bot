import os
from dotenv import load_dotenv

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext 

from db import (get_info_user, boost_and_get_balance, stop_account_and_get_name,
			    delete_user_and_get_name, alarm_exists, save_alarm_detail)

load_dotenv('.env')

TG_API = os.getenv('TG_API')

bot = Bot(token=TG_API)

admin_router = Router()

class MyCallback(CallbackData, prefix='my_callback'):
	id: int
	foo: str


class Dialog(StatesGroup):
	default = State()
	alarm_detail = State()


@admin_router.message(Command('start'))
async def send_welcome_message(message: types.Message, state: FSMContext):
	await state.set_state(Dialog.default)

	await bot.send_message(message.chat.id, 'Здравствуйте, я бот')


@admin_router.message(Dialog.default, Command('profile'))
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


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_balance'))
async def boost_user_balance(query: types.CallbackQuery, callback_data: MyCallback):
	"""Добавляет к балансу ученика 28 дней"""
	id_from_db = callback_data.id

	new_balance = boost_and_get_balance(id_from_db)

	await bot.send_message(query.from_user.id, f'Новый баланс: {new_balance}')


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_pause'))
async def stop_account_user(query: types.CallbackQuery, callback_data: MyCallback):
	"""Приостанавливает счетчик ученика"""
	id_from_db = callback_data.id

	name = stop_account_and_get_name(id_from_db)

	await bot.send_message(query.from_user.id, f'Счётчик {name} приостановлен')


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_delete'))
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


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_delete_validate'))
async def delete_user(query: types.CallbackQuery, callback_data: MyCallback):
	"""Удаляет пользователя из базы"""
	id_from_db = callback_data.id

	name = delete_user_and_get_name(id_from_db)

	await bot.send_message(query.from_user.id, f'Ученик {name} удалён')


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_delete_cancel'))
async def delete_user_cancel(query: types.CallbackQuery, callback_data: MyCallback):
	"""Отменяет удаление пользователя из базы"""
	await bot.send_message(query.from_user.id, f'Удаление отменено')


@admin_router.callback_query(Dialog.default, MyCallback.filter(F.foo == 'inline_button_alarm'))
async def request_do_alarm_detail(query: types.CallbackQuery, callback_data: MyCallback):
	"""Запрашивает у пользователя действие
	   к комментарию к проблеме"""
	id_from_db = callback_data.id

	inline_builder = InlineKeyboardBuilder()

	inline_builder.button(text='Написать комментарий к проблеме', callback_data=MyCallback(
		id=id_from_db, foo='inline_button_alarm_new'))

	if alarm_exists(id_from_db):
		inline_builder.button(text='Дополнить комментарий к проблеме', callback_data=MyCallback(
			id=id_from_db, foo='inline_button_alarm_update'))

	await bot.send_message(query.from_user.id, 'Выберите действие', reply_markup=inline_builder.as_markup())


@admin_router.message(Dialog.default, MyCallback.filter(
	F.foo in ['inline_button_alarm_new', 'inline_button_alarm_update']))
async def request_alarm_detail(query: types.CallbackQuery, callback_data: MyCallback, state: FSMContext):
	"""Запрашивает комментарий к проблеме"""
	await state.set_state(Dialog.alarm_detail)
	await state.update_data(id_from_db=callback_data.id,
		alarm_detail='new' if callback_data.foo == 'inline_button_alarm_new' else 'update')

	await bot.send_message(query.from_user.id, 'Напишите комментарий')


@admin_router.message(Dialog.alarm_detail)
async def save_alarm_detail(message: types.Message, state: FSMContext):
	"""Сохраняет комментарий к проблеме"""
	alarm_detail = message.text

	state_data = await state.get_data()

	id_from_db = state_data.get('id_from_db')

	if state_data.get('alarm_detail') == 'new':
		save_alarm_detail(id_from_db, alarm_detail)
	else:
		save_alarm_detail(id_from_db, alarm_detail, update=True)

	await state.clear()

	await bot.send_message(message.chat.id, 'Комментарий сохранён')