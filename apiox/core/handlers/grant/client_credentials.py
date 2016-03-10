import asyncio
import datetime

from aiohttp.web_exceptions import HTTPForbidden

from ... import db
from ...response import JSONResponse

from .base import BaseGrantHandler

class ClientCredentialsGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_oauth2_client(request)
        if request.token.account != request.token.client:
            return JSONResponse(body={'error': 'access_denied',
                                      'error_description': 'Client and account must match'},
                                base=HTTPForbidden)
        token, (access_token, refresh_token) = \
            db.Token.create_access_token(app=request.app,
                                         session=request.session,
                                         granted_at=datetime.datetime.utcnow(),
                                         client=request.token.client,
                                         account=request.token.account,
                                         user_id=request.token.user_id,
                                         scopes=self.determine_scopes(request),
                                         expires=True,
                                         refreshable=False)
        return JSONResponse(body=token.to_json(access_token=access_token,
                                               refresh_token=refresh_token))
