from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.


def healthcheck(request):
    """Plain-text liveness probe for container platforms (e.g. Render).

    Deliberately independent of the frontend submodule's templates and of
    the database, so it stays green even if migrations are mid-flight or
    FRONTEND_DIR isn't populated — it only proves the app process is up.
    """
    return HttpResponse('ok', content_type='text/plain')
