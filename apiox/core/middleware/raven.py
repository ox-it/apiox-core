import asyncio
import sys

from aiohttp.web_exceptions import HTTPException

@asyncio.coroutine
def raven_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        try:
            return (yield from handler(request))
        except Exception as e:
            if not isinstance(e, HTTPException) and 'raven-client' in app:
                exc_info = sys.exc_info()
                app['raven-client'].captureException(exc_info)
            raise
    return middleware
