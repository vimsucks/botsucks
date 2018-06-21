from peewee import *

from .db import BaseModel


class User(BaseModel):
    id = PrimaryKeyField()
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    username = CharField(null=True)
    is_bot = BooleanField()
