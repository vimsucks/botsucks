from peewee import *
from .db import BaseModel
from .ExpressCompany import ExpressCompany


class ExpressPackage(BaseModel):
    id = PrimaryKeyField()
    logistic_code = CharField()
    company = ForeignKeyField(ExpressCompany)
    description = CharField(null=True)
    state = IntegerField(null=True)
    update_time = DateTimeField(null=True)
    update_station = CharField(null=True)
