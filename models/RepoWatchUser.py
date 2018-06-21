from peewee import *

from .db import BaseModel
from .Repo import Repo
from .User import User


class RepoWatchUser(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User)
    repo = ForeignKeyField(Repo)
