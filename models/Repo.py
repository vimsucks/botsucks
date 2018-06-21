from peewee import *

from .db import BaseModel


class Repo(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
