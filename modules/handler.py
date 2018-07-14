import telegram
import abc
from telegram.ext import CommandHandler


class Handler(object):
    def __init__(self,
                 command,
                 filters=None,
                 allow_edited=False,
                 pass_args=False,
                 pass_update_queue=False,
                 pass_job_queue=False,
                 pass_user_data=False,
                 pass_chat_data=False):
        self.command = command
        self.filters = filters
        self.allow_edited = allow_edited
        self.pass_args = pass_args
        self.pass_update_queue = pass_update_queue
        self.pass_job_queue = pass_job_queue
        self.pass_user_data = pass_user_data
        self.pass_chat_data = pass_chat_data

    @abc.abstractmethod
    def handle(bot: telegram.Bot, update: telegram.Update, args=None):
        pass

    def handler(self):
        return CommandHandler(self.command, self.handle, self.filters, self.allow_edited, self.pass_args,
                              self.pass_update_queue, self.pass_job_queue, self.pass_user_data, self.pass_chat_data)
