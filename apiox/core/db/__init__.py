from sqlalchemy import MetaData

metadata = MetaData()

from .orm import Model

from .authorization_code import *
from .principal import *
from .scope_grant import *
from .token import *

def register_model(orm_mapping, model):
    orm_mapping[model.table] = model

