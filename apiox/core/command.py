def create_models(app):
    import os

    import sqlalchemy

    from .db import metadata

    db_url = os.environ['DB_URL']

    engine = sqlalchemy.create_engine(db_url)
    metadata.create_all(engine)


def run_server(app):
    import asyncio
    import os

    loop = asyncio.get_event_loop()

    f = loop.create_server(app.make_handler(),
                           os.environ['LISTEN_HOST'],
                           int(os.environ.get('LISTEN_PORT', 8000)))
    srv = loop.run_until_complete(f)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass


def shell(app):
    import code
    import readline
    readline.parse_and_bind("tab: complete")
    shell = code.InteractiveConsole({'app': app,
                                     'loop': app.loop})
    shell.interact()
