def create_models(app):
    from .db import Base
    Base.metadata.create_all(app['db'])


def run_server(app):
    import asyncio
    import os

    import logging
    logger = logging.getLogger('apiox.server')

    loop = asyncio.get_event_loop()

    listen_host, listen_port = os.environ['LISTEN_HOST'], int(os.environ.get('LISTEN_PORT', 8000))
    logger.info("Server starting on %s:%d", listen_host, listen_port)
    f = loop.create_server(app.make_handler(), listen_host, listen_port)

    srv = loop.run_until_complete(f)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    logger.info("Server finished.")

def shell(app):
    import code
    import readline
    readline.parse_and_bind("tab: complete")
    shell = code.InteractiveConsole({'app': app,
                                     'loop': app.loop})
    shell.interact()


def declare_apis(app):
    with app['db-session']() as session:
        for api in app['apis']:
            if hasattr(api, 'declare_api'):
                api.declare_api(session)
