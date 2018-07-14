import abc


class RepeatingJob(object):
    def __init__(self, interval, first=None, context=None, name=None):
        self.interval = interval
        self.first = first
        self.context = context
        self.name = name

    @abc.abstractmethod
    def callback(self, bot, callback):
        pass

    def job(self):
        print(self.callback, self.interval, self.first, self.context, self.name)
        return (self.callback, self.interval, self.first, self.context, self.name)
