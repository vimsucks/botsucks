from peewee import *

db = SqliteDatabase('botsucks.db')

class BaseModel(Model):
    class Meta:
        database = db
