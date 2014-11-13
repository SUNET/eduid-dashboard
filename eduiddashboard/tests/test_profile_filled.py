import json
from bson import ObjectId
import re

from mock import patch

from eduid_am.userdb import UserDB
from eduid_am.user import User
from eduiddashboard.testing import LoggedInReguestTests


class ProfileFilledTests(LoggedInReguestTests):

    def test_profile_filled_100(self):
        self.set_logged()
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '100%')

    def test_profile_filled_85(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '85%')

    def test_profile_filled_71(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '71%')

    def test_profile_filled_57(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        user._mongo_doc['preferredLanguage'] = None
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '57%')

    def test_profile_filled_42(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        user._mongo_doc['givenName'] = None
        user._mongo_doc['preferredLanguage'] = None
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '42%')

    def test_profile_filled_28(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        user._mongo_doc['givenName'] = None
        user._mongo_doc['preferredLanguage'] = None
        user._mongo_doc['mailAliases'] = []
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '28%')

    def test_profile_filled_14(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        user._mongo_doc['givenName'] = None
        user._mongo_doc['preferredLanguage'] = None
        user._mongo_doc['mailAliases'] = []
        user._mongo_doc['norEduPersonNIN'] = []
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '14%')

    def test_profile_filled_0(self):
        self.set_logged()
        user = self.userdb.get_user('johnsmith@example.com')
        user.retrieve_modified_ts(self.db.profiles)
        user._mongo_doc['sn'] = None
        user._mongo_doc['displayName'] = None
        user._mongo_doc['givenName'] = None
        user._mongo_doc['preferredLanguage'] = None
        user._mongo_doc['mailAliases'] = []
        user._mongo_doc['norEduPersonNIN'] = []
        user._mongo_doc['mobile'] = []
        self.add_to_session({'user': user})
        response = self.testapp.get('/profile/userstatus/')
        profile_filled = json.loads(response.body)['profile_filled']
        self.assertEquals(profile_filled, '0%')
