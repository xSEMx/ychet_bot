import os

from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from dotenv import load_dotenv

load_dotenv('.env')

TG_API = os.getenv('TG_API')

bot = Bot(token=TG_API)

router = Router()

class MyCallback(CallbackData, prefix='my_callback'):
	foo: str


class Form(StatesGroup):
	form = State()

inline_but_list = []

inline_but = InlineKeyboardButton(
	text='my_inline_button', callback_data=MyCallback(foo='inline_but_1').pack())

inline_but_list.append(inline_but)

inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[inline_but_list])


@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
	await bot.send_message(message.chat.id, 'Hi', reply_markup=inline_keyboard)


@router.message(Command('cancel'))
async def cancel(message: types.Message, state: FSMContext):
	if state.get_state() is None:
		return
	else:
		await state.clear()

	await bot.send_message(message.chat.id, 'Form is clear')

	
@router.callback_query(MyCallback.filter(F.foo == 'inline_but_1'))
async def send_inline(query: types.CallbackQuery, callback_data: MyCallback, state: FSMContext):
	await state.set_state(Form.form)


@router.message(Form.form)
async def send_response_form(message: types.Message, state: FSMContext):
	await state.update_data(form=message.text.split())
	
	state_data = await state.get_data()
	name, age = tuple(state_data.get('form'))

	await bot.send_message(message.chat.id, f'your name: {name}\n your age: {age}')
