import json
from eduiddashboard.testing import LoggedInRequestTests
from eduid_userdb import User

import logging
logger = logging.getLogger(__name__)


class ProfileFilledTests(LoggedInRequestTests):

    def test_profile_filled_100(self):
        profile_filled = self._run_percentage_filled_test([])
        self.assertEquals(profile_filled, '100%')

    def test_profile_filled_85(self):
        profile_filled = self._run_percentage_filled_test(['surname'])
        self.assertEquals(profile_filled, '85%')

    def test_profile_filled_71(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name'])
        self.assertEquals(profile_filled, '71%')

    def test_profile_filled_57(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name', 'language'])
        self.assertEquals(profile_filled, '57%')

    def test_profile_filled_42(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name', 'given_name', 'language'])
        self.assertEquals(profile_filled, '42%')

    def test_profile_filled_28(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name', 'given_name', 'language',
                                                           'mail_addresses'])
        self.assertEquals(profile_filled, '28%')

    def test_profile_filled_14(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name', 'given_name', 'language',
                                                           'mail_addresses', 'nins'])
        self.assertEquals(profile_filled, '14%')

    def test_profile_filled_0(self):
        profile_filled = self._run_percentage_filled_test(['surname', 'display_name', 'given_name', 'language',
                                                           'mail_addresses', 'phone_numbers', 'nins'])
        self.assertEquals(profile_filled, '0%')

    def _run_percentage_filled_test(self, remove):
        self.set_logged()
        user = self.userdb_new.get_user_by_mail('johnsmith@example.com')
        assert isinstance(user, User)  # for the IDE
        saved_user = User(data=user.to_dict())  # save the original user to be able to restore it after the test

        # Remove those parts of the user information that are listed in `remove'
        if 'surname' in remove:
            user.surname = None
        if 'display_name' in remove:
            user.display_name = None
        if 'given_name' in remove:
            user.given_name = None
        if 'language' in remove:
            user.language = None
        if 'mail_addresses' in remove:
            self._empty_user_list(user.mail_addresses)
        if 'phone_numbers' in remove:
            self._empty_user_list(user.phone_numbers)
        if 'nins' in remove:
            self._empty_user_list(user.nins)
        self.dashboard_db.save(user)
        self._save_user_to_userdb(user, old_format=False)

        import pprint
        logger.debug('SAVED USER TO DB:\n{!s}'.format(pprint.pformat(user.to_dict())))

        response = self.testapp.get('/profile/userstatus/')
        self.dashboard_db.save(saved_user, check_sync=False)
        self._save_user_to_userdb(saved_user, old_format=False)
        logger.debug('RESTORED USER IN DB:\n{!s}'.format(pprint.pformat(saved_user.to_dict())))
        return json.loads(response.body)['profile_filled']

    def _empty_user_list(self, what):
        """
        Remove all mail addresses/nins/phone numbers from a User.

        Because of the enforced rules about primary elements in those lists,
        the non-primary elements must be removed first and the primary element last.

        :param what: MailAddressList | NinList | PhoneNumberList
        :return:
        """
        # Must remove non-primary elements first
        [what.remove(x.key) for x in what.to_list() if not x.is_primary]
        [what.remove(x.key) for x in what.to_list()]

    def _save_user_to_userdb(self, user, old_format=True):
        """
        To not depend on having eduid-dashboard-amp available to carry the user
        from profiles to userdb, we just write the updated user into userdb.
        Not ideal, but it is a test case after all.

        :param user:
        :type user: eduid_userdb.User
        :return:
        """
        test_doc = {'_id': user.user_id}
        self.userdb_new._coll.update(test_doc, user.to_dict(old_userdb_format=old_format), upsert=False)
