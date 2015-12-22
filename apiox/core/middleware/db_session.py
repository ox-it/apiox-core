import asyncio


@asyncio.coroutine
def db_session(app, handler):
    @asyncio.coroutine
    def middleware(request):
        with app['db-session']() as session:
            request.session = session
            return (yield from handler(request))
    return middleware