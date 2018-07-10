from peewee import *
from .db import BaseModel
from .CustStudent import CustStudent


class CustLatestSemester(BaseModel):
    id = PrimaryKeyField()
    student = ForeignKeyField(CustStudent)
    name = CharField()
