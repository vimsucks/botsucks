from models import *
from modules import express_company

db.connect()
db.create_tables([Repo,
                  Release,
                  Author,
                  User,
                  RepoWatchUser,
                  LatestReleaseRepo,
                  ExpressPackage,
                  ExpressPackageWatchUser,
                  ExpressCompany,
                  ], safe=True)

for code, name in express_company.items():
    ExpressCompany.create(code=code, name=name)
