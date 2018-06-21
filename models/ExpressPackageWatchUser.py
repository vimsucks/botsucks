from peewee import *

from .db import BaseModel
from .ExpressPackage import ExpressPackage
from .User import User


class ExpressPackageWatchUser(BaseModel):
    id = PrimaryKeyField()
    user = ForeignKeyField(User)
    package = ForeignKeyField(ExpressPackage)
