import aiogrouper
import aiohttp_negotiate

def get_grouper(url, user):
    return aiogrouper.Grouper(url,
        session=aiohttp_negotiate.NegotiateClientSession(negotiate_client_name=user))
