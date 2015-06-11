import json

from aiohttp.web import Response

def JSONResponse(*, body=None, content_type=None, base=Response, **kwargs):
    body = json.dumps(body, indent=2, sort_keys=True).encode()
    if content_type is None:
        content_type = 'application/json'
    return base(body=body, content_type=content_type, **kwargs)
