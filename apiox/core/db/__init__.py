import asyncio

from sqlalchemy import MetaData
from sqlalchemy.sql import select

metadata = MetaData()

class Instance(dict):
    def __init__(self, *args, **kwargs):
        self._updates = {}
        if args:
            self.update(args[0])
        self.update(kwargs)
    
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._updates[key] = value
    
    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._updates.update(*args, **kwargs)

    @staticmethod
    @asyncio.coroutine
    def get(cls, app, **kwargs):
        stmt = select([cls.table]).where(*[getattr(cls.table.c, k) == kwargs[k] for k in kwargs])
        res = yield app['db'].execute(stmt)
        row = yield from res.first()
        if row:
            return cls(row)

    @staticmethod
    @asyncio.coroutine
    def all(cls, app, **kwargs):
        stmt = select([cls.table]).where(*[getattr(cls.table.c, k) == kwargs[k] for k in kwargs])
        res = yield app['db'].execute(stmt)
        rows = yield from res.fetchall()
        return [cls(row) for row in rows]

    @asyncio.coroutine
    def insert(self, app):
        stmt = self.table.insert().values(self)
        yield from app['db'].execute(stmt)
        self._updates.clear()

    @asyncio.coroutine
    def save(self, app):
        pks = self.table.primary_key.columns.keys()
        stmt = self.table.update() \
            .where(*[getattr(self.table.c, pk) == self[pk] for pk in pks]) \
            .values(self._updates)
        yield from app['db'].execute(stmt)
        self._updates.clear()

    @asyncio.coroutine
    def delete(self, app):
        pks = self.table.primary_key.columns.keys()
        stmt = self.table.delete().where(*[getattr(self.table.c, pk) == self[pk] for pk in pks])
        yield from app['db'].execute(stmt)



from .authorization_code import *
from .principal import *
from .scope_grant import *
from .token import *
