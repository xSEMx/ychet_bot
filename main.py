import os

from telegram import start_bot
from db import create_table_users_in_db

def main():
	create_table_users_in_db()
	start_bot()


if __name__ == '__main__':
	main()
