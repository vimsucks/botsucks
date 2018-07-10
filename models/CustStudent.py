from peewee import *
from .db import BaseModel
from .User import User

class CustStudent(BaseModel):
    id = PrimaryKeyField()
    sid = CharField()
    password = CharField()
    user = ForeignKeyField(User)