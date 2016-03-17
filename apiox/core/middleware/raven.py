import asyncio
import sys

from aiohttp.web_exceptions import HTTPException

@asyncio.coroutine
def raven_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        try:
            return (yield from handler(request))
        except HTTPException:
            raise
        except Exception:
            if 'raven-client' in app:
                exc_info = sys.exc_info()
                app['raven-client'].captureException(exc_info, data=request.context)
            raise
    return middleware
