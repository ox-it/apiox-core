import asyncio
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import relationship, backref

from . import Base

__all__ = ['Scope', 'ScopeAlias']

class Scope(Base):
    __tablename__ = 'scope'

    id = Column(String, primary_key=True)
    api_id = Column(String, ForeignKey('api.id'))

    title = Column(String)
    description = Column(String, nullable=True)
    granted_to_user = Column(Boolean, default=False)
    personal = Column(Boolean, default=False)
    lifetime = Column(Integer, nullable=True)
    advertise = Column(Boolean, default=False)

    aliases = relationship('ScopeAlias', order_by='ScopeAlias.id', backref='scope',
                           cascade="all, delete, delete-orphan")

    def __str__(self):
        return '{} ({})'.format(self.id, self.title)

    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'grantedToUser': self.granted_to_user,
            'personal': self.personal,
            'lifetime': self.lifetime,
            'advertise': self.advertise,
            'aliases': [alias.id for alias in self.aliases],
        }

    @classmethod
    def from_json(cls, api_id, data):
        return Scope(
            id=data['id'],
            api_id=api_id,
            title=data['title'],
            description=data.get('description') or None,
            granted_to_user=data.get('grantedToUser', False),
            personal=data.get('personal', False),
            lifetime=data.get('lifetime'),
            advertise=data.get('advertise', False),
            aliases=[ScopeAlias(id=alias, scope_id=data['id']) for alias in data.get('aliases', ())]
        )

class ScopeAlias(Base):
    __tablename__ = 'scope_alias'

    id = Column(String, primary_key=True)
    scope_id = Column(String, ForeignKey('scope.id'))

    #scope = relationship('Scope', backref=backref('aliases', order_by=id))
