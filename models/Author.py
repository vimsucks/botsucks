from peewee import *
from .db import BaseModel


class Author(BaseModel):
    id = IntegerField(primary_key=True)
    username = CharField()
    api_url = CharField()
    url = CharField()
