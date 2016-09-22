import asyncio
import datetime
import logging

from aiohttp.web_exceptions import HTTPException
from multidict._multidict import CIMultiDict, MultiDict

from apiox.core.token import generate_token

logger = logging.getLogger("apiox.request")


@asyncio.coroutine
def request_logging_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        start_dt = datetime.datetime.now(tz=datetime.timezone.utc)
        server_name, server_port, *_ = request.transport.get_extra_info('sockname')
        assert isinstance(request.headers, MultiDict)
        # Workaround, pending https://github.com/aio-libs/multidict/issues/11
        # headers = request.headers.copy()
        headers = CIMultiDict((str(k), v) for k, v in request.headers.items())
        if headers.get('Authorization'):
            headers['Authorization'] = headers['Authorization'].split()[0] + ' [redacted]'
        if headers.get('Cookie'):
            headers['Cookie'] = '[redacted]'
        request.context = {
            'user': {},
            'request': {
                'url': '{}://{}{}'.format(request.scheme, request.host, request.path),
                'query_string': request.query_string,
                'method': request.method,
                'headers': dict(headers),
                'env': {
                    'REMOTE_ADDR': request.headers.get('X-Forwarded-Host') or
                                   request.transport.get_extra_info('peername')[0],
                    'SERVER_NAME': server_name,
                    'SERVER_PORT': server_port,
                },
            },
            'tags': {
                'request_id': generate_token(),
                'parent_request_id': request.headers.get('X-Parent-Request-ID'),
                'route': request.match_info.route.name,
            },
            'extra': {},
        }
        try:
            response = (yield from handler(request))
        except HTTPException as e:
            response = e
            raise
        except BaseException:
            response = None
            raise
        finally:
            end_dt = datetime.datetime.now(tz=datetime.timezone.utc)
            if getattr(request, 'token', None):
                request.context['user'].update({
                    'id': request.token.account.id,
                    'username': request.token.account.name,
                })
                request.context['tags'].update({
                    'client_id': request.token.client_id,
                    'client_name': request.token.client.name,
                    'user_id': request.token.user_id,
                })
            request.context['extra'].update({
                'status': 500 if response is None else response.status,
                'duration': (end_dt - start_dt).total_seconds(),
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
            })
            if getattr(request, 'api', None):
                request.context['tags']['api'] = request.api.id
            if response is not None:
                request.context['extra'].update({
                   'responseContentType': response.headers.get('Content-Type'),
                   'responseContentLength': response.content_length,
                   'responseLocation': response.headers.get('Location'),
                })
            
            logger.info("%s %s %s %dms",
                        request.method, request.path,
                        request.context['extra']['status'],
                        request.context['extra']['duration'] * 1000,
                        extra=request.context)
        return response
    return middleware

