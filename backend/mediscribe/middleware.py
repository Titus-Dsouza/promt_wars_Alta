"""Restrict development CORS to the documented local frontend server."""

from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers


class DevelopmentCORSMiddleware:
    """Allow credentialed local frontend requests without wildcard origins."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('Origin')
        local_origins = set(getattr(settings, 'CSRF_TRUSTED_ORIGINS', ()))
        is_local_frontend = settings.DEBUG and origin in local_origins

        if request.method == 'OPTIONS' and is_local_frontend:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if is_local_frontend:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, X-Requested-With'
            patch_vary_headers(response, ('Origin',))

        return response
