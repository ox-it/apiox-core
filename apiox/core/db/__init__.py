from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .api import *
from .authorization_code import *
from .principal import *
from .scope_grant import *
from .token import *

def register_model(orm_mapping, model):
    orm_mapping[model.table] = model

