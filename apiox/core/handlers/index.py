import asyncio
import logging

from .base import BaseHandler
from ..response import JSONResponse

from apiox.core import __version__
from apiox.core.db import API

logger = logging.getLogger(__name__)

class IndexHandler(BaseHandler):
    @asyncio.coroutine
    def get(self, request):
        body = {
            'title': 'University of Oxford API',
            'version': __version__,
            '_links': {
                'self': {'href': request.app.router['index'].url()},
                'oauth2:token': {'href': request.app.router['oauth2:token'].url()},
                'oauth2:authorize': {'href': request.app.router['oauth2:authorize'].url()},
            },
        }

        with request.app['db-session']() as session:
            for api in session.query(API).filter_by(advertise=True).all():
                link = {'title': api.title}
                if not api.base:
                    try:
                        link['href'] = request.app.router[api.id + ':index'].url()
                    except KeyError:
                        logger.warning("API %s has no index handler", api.id)
                        continue
                else:
                    link['href'] = '/{}/'.format(api.id)
                body['_links']['app:' + api.id] = link
        
        return JSONResponse(body=body)
