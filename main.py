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
    dispatcher.add_handler(GithubHandler().handler())
    dispatcher.add_handler(ExpressHandler().handler())
    dispatcher.add_handler(CustHandler().handler())
    dispatcher.add_handler(HelpHandler().handler())

    job_queue = updater.job_queue
    job_queue.run_repeating(*GithubJob().job())
    job_queue.run_repeating(*ExpressJob().job())
    job_queue.run_repeating(*CustJob().job())

    logging.info('Starting bot...')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
