from pyramid.response import FileResponse
from pyramid.view import view_config

import os


@view_config(name='favicon.ico')
def favicon_view(context, request):
    path = os.path.dirname(__file__)
    icon = os.path.join(path + '/../', 'static', 'favicon.ico')
    return FileResponse(icon, request=request)
