class IUserDB:

    def __init__(self, request):
        self.request = request

    def get_user(self, userid):
        return {}

    class DuplicatedUser(Exception):
        pass

    class MultipleUsersReturned(Exception):
        pass
