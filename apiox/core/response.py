import json

from aiohttp.web import Response
from aiohttp.web_exceptions import HTTPException

def JSONResponse(*, body=None, content_type=None, base=Response, **kwargs):
    body = json.dumps(body, indent=2).encode()
    if content_type is None:
        content_type = 'application/json'
    return base(body=body, content_type=content_type, **kwargs)
