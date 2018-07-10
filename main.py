import logging
from telegram.ext import Updater, CommandHandler

import config
from modules import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Hello World')


def main():
    updater = Updater(token=config.TELEGRAM_API_TOKEN)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('gh_release', github.handle, pass_args=True))
    dispatcher.add_handler(CommandHandler('express', express.handle, pass_args=True))
    dispatcher.add_handler(CommandHandler('cust', cust.handle, pass_args=True))
    dispatcher.add_handler(CommandHandler('test', test.handle, pass_args=True))
    # dispatcher.add_handler(user.minute_command_handler)

    job_queue = updater.job_queue
    job_queue.run_repeating(github.callback_check_releases, interval=60*30, first=0)
    job_queue.run_repeating(express.callback_check_express, interval=60*30, first=0)
    job_queue.run_repeating(cust.callback_check_score, interval=60*30, first=0)

    logging.info('Starting bot...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
