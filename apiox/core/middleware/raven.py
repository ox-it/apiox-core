import raven

import asyncio
import sys

@asyncio.coroutine
def raven_middleware(app, handler):
    @asyncio.coroutine
    def middleware(request):
        try:
            return (yield from handler(request))
        except Exception:
            print("X")
            if 'raven-client' in app:
                print("Y")
                exc_info = sys.exc_info()
                app['raven-client'].captureException(exc_info)
            raise
    return middleware
