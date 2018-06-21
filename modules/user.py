import telegram
from telegram.ext import CommandHandler

from models import *


""" def handle_minute_command(bot, update: telegram.Update):
    user = update.message.from_user
    insert_user(user)
    minute_registered_user_query = MinuteRegisteredUser.select().where(MinuteRegisteredUser.user_id == user.id)
    if not minute_registered_user_query.exists():
        MinuteRegisteredUser.create(user_id=user.id)
    else:
        bot.send_message(update.message.chat_id, text='Error! You have already registered')
        """


def insert_user(user: telegram.User):
    user_query = User.select().where(User.id == user.id)
    if not user_query.exists():
        User.create(id=user.id, first_name=user.first_name, last_name=user.last_name, username=user.username,
                    is_bot=user.is_bot)


"""
def callback_minute(bot, job):
    minute_registered_users = MinuteRegisteredUser.select()
    for minute_registered_user in minute_registered_users:
        user = minute_registered_user.user
        print(user)
        bot.send_message(user.id, text='Minute message')
        """


#minute_command_handler = CommandHandler('minute', handle_minute_command)
