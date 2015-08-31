import os
import sys

import sqlalchemy

from . import metadata

try:
    db_url = os.environ['DB_URL']
except KeyError:
    db_url = sys.argv[1]

engine = sqlalchemy.create_engine(db_url)
metadata.create_all(engine)
