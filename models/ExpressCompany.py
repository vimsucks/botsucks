from peewee import *
from .db import BaseModel


class ExpressCompany(BaseModel):
    id = PrimaryKeyField()
    code = CharField()
    name = CharField()
