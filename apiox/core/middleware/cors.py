simple_headers = {
    'Cache-Control',
    'Content-Language',
    'Content-Type',
    'Expires',
    'Last-Modified',
    'Pragma',
    'Content-Length', # not a simple header, but no need to expose
}
simple_headers = set(name.upper() for name in simple_headers)

def add_cors_headers(request, response):
    if 'Origin' in request.headers:
        expose_headers = {name for name in response.headers if name.upper() not in simple_headers}
        if expose_headers:
            response.headers['Access-Control-Expose-Headers'] = ', '.join(expose_headers)
        if 'Access-Control-Request-Method' in request.headers:
            response.headers['Access-Control-Allow-Method'] = request.headers['Access-Control-Request-Method']
        if 'Access-Control-Request-Headers' in request.headers:
            response.headers['Access-Control-Allow-Headers'] = request.headers['Access-Control-Request-Headers']
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
