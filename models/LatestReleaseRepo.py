from peewee import *

from .db import BaseModel
from . import Repo, Release

class LatestReleaseRepo(BaseModel):
    id = PrimaryKeyField()
    release = ForeignKeyField(Release)
    repo = ForeignKeyField(Repo)
