from pyramid.security import authenticated_userid


# Only authentication is required for edit the user profile
def groupfinder(userid, request):
    if authenticated_userid(request):
        return ['group:owner']
    else:
        return []
