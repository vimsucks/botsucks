from models import *

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
