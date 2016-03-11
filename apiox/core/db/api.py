import asyncio
from sqlalchemy import Table, Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from sqlalchemy.orm import relationship

from apiox.core.token import TOKEN_LENGTH
from . import Base
from .scope import Scope

__all__ = ['API']


api_administrator = Table('api_administrator', Base.metadata,
    Column('api_id', String, ForeignKey('api.id'), primary_key=True),
    Column('administrator_id', String(TOKEN_LENGTH), ForeignKey('principal.id'), primary_key=True),
)


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

    paths = Column(JSON, default=[])

    scopes = relationship('Scope', order_by='Scope.id', backref='api',
                          cascade="all, delete, delete-orphan, save-update")

    administrators = relationship('Principal', secondary=api_administrator,
                                    primaryjoin=(id==api_administrator.c.administrator_id),
                                    secondaryjoin=(id==api_administrator.c.api_id))

    def to_json(self, app, may_administrate=False):
        data = {
            'id': self.id,
            'title': self.title,
            'raml': self.raml,
            'available': self.available,
            'href': app.router['api:dispatch'].url(parts={'api_id': self.id, 'path': ''}),
            '_links': {
                'self': {
                    'href': app.router['api:detail'].url(parts={'id': self.id}),
                },
            },
        }
        if may_administrate:
            data.update({
                'base': self.base,
                'advertise': self.advertise,
                'paths': self.paths,
                'scopes': [scope.to_json() for scope in self.scopes],
                'requireScope': self.require_scope,
                'requireUser': self.require_user,
                'requireAuth': self.require_auth,
                'requireRole': self.require_role,
                'requireGroup': self.require_group,
            })
        return data

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
            advertise=data.get('advertise', True),
            available=data.get('available', True),
            paths=data.get('paths') or [],
            scopes=[Scope.from_json(data['id'], scope) for scope in data.get('scopes', ())]
        )

    def may_administrate(self, token):
        if not token:
            return False
        if token.account not in self.administrators:
            return False
        if not any(s.id == '/api/manage' for s in token.scopes):
            return False
        return True
