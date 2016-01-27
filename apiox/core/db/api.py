import asyncio
from sqlalchemy import Table, Column, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from . import Base
from .scope import Scope

__all__ = ['API']

class API(Base):
    __tablename__ = 'api'

    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String, nullable=True)
    raml = Column(String, nullable=True)
    base = Column(String)

    require_scope = Column(ARRAY(String), default=[])
    require_user = Column(Boolean, default=False)
    require_auth = Column(Boolean, default=False)
    require_role = Column(ARRAY(String), default=[])
    require_group = Column(String)

    advertise = Column(Boolean, default=True)
    available = Column(Boolean, default=True)

    paths = Column(JSONB, default=[])

    scopes = relationship('Scope', order_by='Scope.id', backref='api',
                          cascade="all, delete, delete-orphan, save-update")

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'raml': self.raml,
            'base': self.base,
            'requireScope': self.require_scope,
            'requireUser': self.require_user,
            'requireAuth': self.require_auth,
            'requireRole': self.require_role,
            'requireGroup': self.require_group,
            'advertise': self.advertise,
            'available': self.available,
            'paths': self.paths,
            'scopes': [scope.to_json() for scope in self.scopes],
        }

    @classmethod
    def from_json(cls, data):
        return API(
            id=data['id'],
            title=data['title'],
            raml=data.get('raml'),
            base=data.get('base'),
            require_scope=data.get('scope', []),
            require_user=data.get('user') or False,
            require_auth=data.get('requireAuth') or False,
            require_group=data.get('requireGroup'),
            advertise=data.get('advertise') or True,
            available=data.get('available') or True,
            paths=data.get('paths') or [],
            scopes=[Scope.from_json(data['id'], scope) for scope in data.get('scopes', ())]
        )
