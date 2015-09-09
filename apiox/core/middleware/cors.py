def add_cors_headers(request, response):
    if 'Origin' in request.headers:
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']
        if 'Access-Control-Request-Method' in request.headers:
            response.headers['Access-Control-Allow-Method'] = request.headers['Access-Control-Request-Method']
        if 'Access-Control-Request-Headers' in request.headers:
            response.headers['Access-Control-Allow-Headers'] = request.headers['Access-Control-Request-Headers']
