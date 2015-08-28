import asyncio

from sqlalchemy import MetaData
from sqlalchemy.sql import select

metadata = MetaData()

_orm_mapping = {}

from .orm import Instance

from .authorization_code import *
from .principal import *
from .scope_grant import *
from .token import *

for _obj in dict(locals()).values():
    if isinstance(_obj, type) and issubclass(_obj, Instance) and _obj is not Instance:
        _orm_mapping[_obj.table] = _obj
