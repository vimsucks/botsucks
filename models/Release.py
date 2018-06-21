from peewee import *
from .db import BaseModel
from .Repo import Repo
from .Author import Author



class Release(BaseModel):
    id = IntegerField(primary_key=True)
    repo = ForeignKeyField(Repo)
    api_url = CharField()
    url = CharField()
    name = CharField()
    author = ForeignKeyField(Author)
    created_at = DateTimeField()
    published_at = DateTimeField()
