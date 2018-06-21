import telegram


def handle(bot: telegram.Bot, update: telegram.Update, args):
    print(args)
