import sqlite3
import datetime
from typing import Union

DATABASE = 'database.db' # path to your database

class SqlConnection:
	"""Контекстный менеджер для удобного соединения:
	   на входе открывает соединение, на выходе комитит
	   и закрывает соединение"""
	def __init__(self, database=DATABASE):
		self.database = database


	def __enter__(self) -> sqlite3.Connection:
		self.conn = sqlite3.connect(self.database)
		return self.conn


	def __exit__(self, type, value, traceback):
		self.conn.commit()
		self.conn.close()


def __calculate_age(birthday: datetime.date) -> int:
	"""Вычисляет возраст по дате дня рождения"""
	difference = datetime.date.today() - birthday
	age = difference.days // 365
	return age


def __calculate_currency(course: int) -> str:
	"""Вычисляет валюту по классу"""
	if course == 0:
		return 'IDR'
	else:
		return 'USD'


def __calculate_price(course: int, discount: int, habitation: bool) -> int:
	"""Вычисляет цену за обучение исходя из
	   класса, скидки, проживания"""
	if course == 0:
		price = 8_000_000 * (1 - discount / 100) # Валюта IDR
	elif 1 <= course <= 4:
		start_price = 800 if not habitation else 800 + 400
		price = start_price * (1 - discount / 100) # Валюта USD
	else:
		start_price = 1000 if not habitation else 1000 + 400
		price = start_price * (1 - discount / 100) # Валюта USD
	return price


def create_table_users_in_db():
	"""Создаёт таблицу users, если она не создана"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		try:
			cursor.execute("SELECT COUNT(id) FROM users") # проверяем наличие таблицы users
		except sqlite3.OperationalError:
			conn.create_function('calculate_age', 1, __calculate_age)
			conn.create_function('calculate_currency', 1, __calculate_currency)
			conn.create_function('calculate_price', 3, __calculate_price)

			cursor.execute(
				"""
					CREATE TABLE users
					(
						id INTEGER PRIMARY KEY AUTOINCREMENT,
						name TEXT NOT NULL,
						birthday DATE NOT NULL CHECK (birthday < CURRENT_TIMESTAMP),
						age INTEGER NOT NULL DEFAULT 0, /* DEFAULT 0 так как дальше используем TRIGGER */
						date_enrollment DATE NOT NULL,
						course INTEGER NOT NULL CHECK (course BETWEEN 0 and 9),
						habitation BOOlEAN NOT NULL,
						discount INTEGER NOT NULL DEFAULT 0 CHECK (discount BETWEEN 0 and 100),
						currency TEXT NOT NULL DEFAULT '', /* DEFAULT '' так как дальше используем TRIGGER */
						price INTEGER NOT NULL DEFAULT 0, /* DEFAULT 0 так как дальше используем TRIGGER */
						balance INTEGER DEFAULT 0,
						parent_id INTEGER,
						child_id INTEGER UNIQUE,
						pause BOOlEAN NOT NULL DEFAULT FALSE,
						comment TEXT,
						alarm BOOlEAN NOT NULL DEFAULT FALSE,
						alarm_detail TEXT CHECK
							(alarm AND alarm_detail IS NOT NULL OR NOT alarm AND alarm_detail IS NULL),
						penalty INTEGER
					)
				"""
			)

			cursor.execute(
				"""
					CREATE TRIGGER trigger
					AFTER INSERT ON users
					FOR EACH ROW
					BEGIN
						UPDATE users
						SET age = calculate_age(NEW.birthday), currency = calculate_currency(NEW.course),
							price = calculate_price(NEW.course, NEW.discount, NEW.habitation)
						WHERE id = NEW.id;
					END;
				"""
			)


def save_telegram_user_id_and_get_name(id_: int, telegram_id: int, type_user: str) -> str:
	"""Сохраняет telegram_id пользователя в базе и возвращает имя этого пользователя"""
	with SqlConnection() as conn:
		cursor = conn.cursor()
		
		if type_user == 'parent':
			field = 'parent_id'
		elif type_user == 'child':
			filed = 'child_id'

		telegram_field = cursor.execute(f"SELECT {field} FROM users WHERE id = {id_}").fetchone()[0]

		if telegram_field is not None:
			raise ValueError

		cursor.execute(f"UPDATE users SET {field} = {telegram_id} WHERE id = {id_}")

		name = cursor.execute(f"SELECT name FROM users WHERE id = {id_}").fetchone()[0]

		return name


def get_type_telegram_user(telegram_id: int) -> Union[str, None]:
	"""Возвращает тип пользователя (родитель или ребёнок)
	   по telegram_id"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		result = cursor.execute(
			f"""
				SELECT
					CASE
						WHEN parent_id = {telegram_id} THEN 'parent'
						WHEN child_id = {telegram_id} THEN 'child'
						ELSE NULL
					END AS result
				FROM users
			"""
		).fetchone()[0]

		return result


def get_balance(child_id: int) -> int:
	"""Возвращает баланс ребёнка по child_id"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		balance = cursor.execute(
			f"SELECT balance FROM users WHERE child_id = {child_id}").fetchone()[0]

		return balance


def get_list_with_dicts_with_names_and_balances(parent_id: int) -> list:
	"""Возвращает список cо словарями имён детей родителя и их балансами"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		data_query = cursor.execute(
			f"SELECT name, balance FROM users WHERE parent_id = {parent_id}").fetchall()

		names_and_balances = list(map(
			lambda data: {'name': data[0], 'balance': data[1]}, data_query))

		return names_and_balances


def get_info_user(id_: int) -> dict:
	"""Возвращает словарь с информацией о ребёнке"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		data_query = cursor.execute(
			f"""
				SELECT name, id, age, course, date_enrollment, habitation,
					balance, comment, alarm_detail, parent_id
				WHERE id = {id_}
			"""
		).fetchone()

		columns = [column[0] for column in cursor.description()]

		info = dict(zip(columns, data_query))
		
		return info


def boost_and_get_balance(id_: int) -> int:
	"""Добавляет к балансу ученика 28 дней и возвращает его"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		cursor.execute(f"UPDATE users SET balance = balance + 28 WHERE id = {id_}")		

		new_balance = cursor.execute(f"SELECT balance FROM users WHERE id = {id_}").fetchone()[0]

		return new_balance


def stop_account_and_get_name(id_: int) -> str:
	"""Устанавливает pause=True в базе и возвращает имя ученика"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		cursor.execute(f"UPDATE users SET pause = 1 WHERE id = {id_}")

		name = cursor.execute(f"SELECT name WHERE id = {id_}").fetchone()[0]

		return name


def delete_user_and_get_name(id_: int) -> str:
	"""Удаляет ученика из базы и возвращает его имя"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		name = cursor.execute(f"SELECT name FROM users WHERE id = {id_}").fetchone()[0]

		cursor.execute(f"DELETE FROM users WHERE id = {id_}")

		return name


def alarm_exists(id_: int) -> bool:
	"""Проверяет установлено ли у пользователя alarm=True"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		query = cursor.execute(f"SELECT EXISTS(SELECT id FROM users WHERE alarm = True and id = {id_})")

		if query.fetchone()[0]:
			return True
		else:
			return False


def save_alarm_detail(id_: int, alarm_detail: str, update=None) -> None:
	"""Сохраняет комментарий к проблеме"""
	with SqlConnection() as conn:
		cursor = conn.cursor()

		if update is not None:
			alarm_detail_old = cursor.execute(
				f"SELECT alarm_detail FROM users WHERE id = {id_}").fetchone()[0]

			alarm_detail = alarm_detail_old + alarm_detail

			query = f"UPDATE users SET alarm_detail = {alarm_detail} WHERE id = {id_}"

		else:
			query = f"UPDATE users SET alarm = True and alarm_detail = {alarm_detail} WHERE id = {id_}"

		cursor.execute(query)


with SqlConnection() as conn:
	cursor = conn.cursor()
	conn.create_function('calculate_age', 1, __calculate_age)
	conn.create_function('calculate_currency', 1, __calculate_currency)
	conn.create_function('calculate_price', 3, __calculate_price)

	for i in range(6):
		name = input()
		birthday = datetime.date(int(input()), int(input()), int(input()))
		date_enrollment = datetime.date(int(input()), int(input()), int(input()))
		course = int(input())
		habitation = False

		cursor.execute(
			"""INSERT INTO users (name, birthday, date_enrollment, course, habitation)
			    VALUES (?, ?, ?, ?, ?)
			""", (name, birthday, date_enrollment, cursor, habitation)
		)

		print('[+]')