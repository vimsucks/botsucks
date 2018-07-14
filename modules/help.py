import telegram

from .handler import Handler


class HelpHandler(Handler):

    def __init__(self):
        super().__init__("help")

    def handle(self, bot: telegram.Bot, update: telegram.Update, args=None):
        bot.send_message(update.message.chat_id, "TODO: print help message")
