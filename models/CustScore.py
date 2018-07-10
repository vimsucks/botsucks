from peewee import *
from .db import BaseModel
from .CustStudent import CustStudent


class CustScore(BaseModel):
    id = PrimaryKeyField()
    student = ForeignKeyField(CustStudent)
    name = CharField()
    classification = CharField()
    credit = FloatField()
    period = IntegerField()
    score = CharField()
    review = CharField()
    exam_type = CharField()

    def __eq__(self, other):
        return self.score == other.score and self.review == other.review
