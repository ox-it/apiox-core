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
    # There's a bug in iOS that means that 401 responses are hidden if there's a Basic challenge in the
    # WWW-Authenticate header. This lets clients request that the header be renamed so as not to trigger it.
    # See e.g. http://stackoverflow.com/questions/11025213/ios-authentication-using-xmlhttprequest-handling-401-reponse
    # for more details.
    if 'X-Rename-WWW-Authenticate' in request.headers and \
                    'WWW-Authenticate' in response.headers and \
                    request.headers['X-Rename-WWW-Authenticate'] not in response.headers:
        for key, value in response.headers.items():
            if key.upper() == 'WWW-Authenticate'.upper():
                response.headers.add(request.headers['X-Rename-WWW-Authenticate'], value)
        del response.headers['WWW-Authenticate']

    if 'Origin' in request.headers:
        expose_headers = {name for name in response.headers if name.upper() not in simple_headers}
        if expose_headers:
            response.headers['Access-Control-Expose-Headers'] = ', '.join(expose_headers)
        if 'Access-Control-Request-Method' in request.headers:
            response.headers['Access-Control-Allow-Method'] = request.headers['Access-Control-Request-Method']
        if 'Access-Control-Request-Headers' in request.headers:
            response.headers['Access-Control-Allow-Headers'] = request.headers['Access-Control-Request-Headers']
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
