import asyncio
import datetime

from sqlalchemy.orm.exc import NoResultFound

from ... import db
from ...response import JSONResponse

from .base import BaseGrantHandler
from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden
from apiox.core.token import hash_token

class AuthorizationCodeGrantHandler(BaseGrantHandler):
    @asyncio.coroutine
    def __call__(self, request):
        yield from self.require_oauth2_client(request, grant_type='authorization_code')
        
        try:
            code = request.POST['code']
        except KeyError:
            self.oauth2_exception(HTTPBadRequest, request,
                                  {'error': 'invalid_request',
                                   'error_description': "Missing `code` parameter"})
        
        code_hash = hash_token(request.app, code)
        try:
            code = request.session.query(db.AuthorizationCode).filter_by(code_hash=code_hash).one()
        except NoResultFound:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Unrecognised authorization code'})

        if code.expire_at < datetime.datetime.utcnow():
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'The authorization code has expired'})

        if code.redirect_uri and code.redirect_uri != request.POST.get('redirect_uri'):
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'access_denied',
                                   'error_description': 'Incorrect `redirect_uri` specified'})

        token, (access_token, refresh_token) = code.convert_to_access_token(request.app,
                                                                            request.session)
        return JSONResponse(body=token.to_json(access_token=access_token,
                                               refresh_token=refresh_token))
