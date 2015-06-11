import asyncio
import datetime
import logging

from aiohttp.web_exceptions import HTTPException

logger = logging.getLogger("apiox.request")

@asyncio.coroutine
def request_logging_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        start_dt = datetime.datetime.now(tz=datetime.timezone.utc)
        try:
            response = (yield from handler(request))
        except HTTPException as e:
            response = e
            raise
        except BaseException:
            response = None
            raise
        finally:
            status = 500 if response is None else response.status
            end_dt = datetime.datetime.now(tz=datetime.timezone.utc)
            extra = {
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
                'duration': (end_dt - start_dt).total_seconds(),
                'method': request.method,
                'path': request.path,
                'query': request.query_string,
                'route': request.match_info.route.name,
                'userAgent': request.headers.get('User-Agent'),
                'requestAccept': request.headers.get('Accept'),
                'requestContentType': request.headers.get('Content-Type'),
                'requestContentLength': request.content_length,
                'status': status,
            }
            if hasattr(request, 'token'):
                extra.update({
                   'user': request.token.user,
                   'client': request.token.client,
                   'account': request.token.account,
                })
            if response is not None:
                extra.update({
                   'responseContentType': response.headers.get('Content-Type'),
                   'responseContentLength': response.content_length,
                   'responseLocation': response.headers.get('Location'),
                })
            
            logger.info("%s %s %s", request.method, request.path, status,
                        extra=extra)
        return response
    return middleware
