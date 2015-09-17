import asyncio
import collections

from sqlalchemy.sql import select


class Model(collections.OrderedDict):
    def __init__(self, app, *args, **kwargs):
        super().__init__()
        self._app = app
        self._updates = {}
        self._foreign = {}
        super().update({c.name: None for c in self.table.columns})
        if args:
            self.update(args[0])
        self.update(kwargs)
    
    def __setitem__(self, key, value):
        if key not in self.table.columns:
            raise KeyError(key)
        super().__setitem__(key, value)
        self._updates[key] = value
    
    def update(self, other):
        for key in other:
            if key not in self.table.columns:
                raise KeyError(key)
        super().update(other)
        self._updates.update(other)

    @classmethod
    @asyncio.coroutine
    def get(cls, app, **kwargs):
        stmt = select([cls.table]).where(*[getattr(cls.table.c, k) == kwargs[k] for k in kwargs])
        with (yield from app['db']) as conn:
            res = yield from conn.execute(stmt)
            row = yield from res.first()
        if row:
            return cls(app, row)

    @classmethod
    @asyncio.coroutine
    def all(cls, app, *args, **kwargs):
        stmt = select([cls.table]).where(*(list(args) + [getattr(cls.table.c, k) == kwargs[k] for k in kwargs]))
        with (yield from app['db']) as conn:
            res = yield from conn.execute(stmt)
            rows = yield from res.fetchall()
        return [cls(app, row) for row in rows]

    @asyncio.coroutine
    def insert(self):
        stmt = self.table.insert().values(self)
        with (yield from self._app['db']) as conn:
            yield from conn.execute(stmt)
        self._updates.clear()

    @asyncio.coroutine
    def save(self):
        pks = self.table.primary_key.columns.keys()
        stmt = self.table.update() \
            .where(*[getattr(self.table.c, pk) == self[pk] for pk in pks]) \
            .values(self._updates)
        with (yield from self._app['db']) as conn:
            yield from conn.execute(stmt)
        self._updates.clear()

    @asyncio.coroutine
    def delete(self):
        pks = self.table.primary_key.columns.keys()
        stmt = self.table.delete().where(*[getattr(self.table.c, pk) == self[pk] for pk in pks])
        with (yield from self._app['db']) as conn:
            yield from conn.execute(stmt)

    @asyncio.coroutine
    def _get_related(self, name):
        if name not in self._foreign:
            col = self.table.columns[name]
            for fk in col.foreign_keys:
                break
            else:
                raise IndexError
            rel_col = fk.column
            rel_instance = self._app['orm_mapping'][rel_col.table]
            self._foreign[name] = yield from rel_instance.get(self._app, **{rel_col.name: self[name]})
        return self._foreign[name]

    def __getattr__(self, name):
        if name in self:
            return self[name]
        elif (name + '_id') in self and self.table.columns[name + '_id'].foreign_keys:
            return self._get_related(name + '_id')
        else:
            raise AttributeError(name)
