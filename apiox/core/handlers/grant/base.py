
from aiohttp.web_exceptions import HTTPForbidden

from ..base import BaseHandler
from ...response import JSONResponse

class BaseGrantHandler(BaseHandler):
    def require_oauth2_client(self, request):
        self.require_authentication(request)
        if '/oauth2/client' not in request.token.scopes:
            self.oauth2_exception(HTTPForbidden, request,
                                  {'error': 'unauthorized_client',
                                   'error_description': "Your client isn't registered as an OAuth2 client."})

    def determine_scopes(self, request):
        scopes = set(request.token.scopes)
        if 'scopes' in request.POST:
            scopes &= set(request.POST['scopes'].split())
        else:
            scopes.discard('/oauth2/client')
            scopes.discard('/oauth2/user')
        return scopes

    def oauth2_exception(self, exception_class, request, body):
        if 'state' in request.POST:
            body['state'] = request.POST['state']
        raise JSONResponse(base=exception_class,
                           body=body)
