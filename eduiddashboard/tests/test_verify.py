import datetime

from unittest import TestCase
from eduid_userdb import User
from eduid_userdb.testing import MOCKED_USER_STANDARD
from copy import deepcopy

from eduiddashboard.verifications import (_remove_mail_from_user, _add_mail_to_user,
                                          _remove_phone_from_user, _add_phone_to_user,
                                          _remove_nin_from_user, _add_nin_to_user)
from eduiddashboard.testing import LoggedInRequestTests


class TestRemoveMailFromUser(TestCase):

    def setUp(self):
        mailuser = deepcopy(MOCKED_USER_STANDARD)
        mailuser.update({
            'mail': 'firstverified@example.com',
            'mailAliases':
                [{'email': 'firstverified@example.com',
                  'verified': True,
                  },
                 {'email': 'secondverified@example.com',
                  'verified': True,
                  },
                 {'email': 'first_not_verified@example.com',
                  'verified': False,
                  }],
        })
        self.mailuser = User(data = mailuser)

    def test_remove_primary_mail(self):
        """ Remove the primary address and expect the next verified one to be promoted to primary """
        this = _remove_mail_from_user('firstverified@example.com', self.mailuser)
        expected = [{'email': 'secondverified@example.com',
                     'verified': True,
                     'primary': True,
                     },
                    {'email': 'first_not_verified@example.com',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.mail_addresses.to_list_of_dicts(), expected)

    def test_remove_verified_mail(self):
        """ Remove a verified non-primary address """
        this = _remove_mail_from_user('secondverified@example.com', self.mailuser)
        expected = [{'email': 'firstverified@example.com',
                     'verified': True,
                     'primary': True,
                     },
                    {'email': 'first_not_verified@example.com',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.mail_addresses.to_list_of_dicts(), expected)

    def test_remove_nonverified_mail(self):
        """ Remove a non-verified address, although this user would not be found in reality """
        this = _remove_mail_from_user('first_not_verified@example.com', self.mailuser)
        expected = [{'email': 'firstverified@example.com',
                     'verified': True,
                     'primary': True,
                     },
                    {'email': 'secondverified@example.com',
                     'verified': True,
                     'primary': False,
                     }]
        self.assertEqual(this.mail_addresses.to_list_of_dicts(), expected)

    def test_add_new_email_address(self):
        """ Add a new email address to the test user """
        this = self.mailuser
        _add_mail_to_user('thirdverified@example.com', this)
        expected = [{'email': 'firstverified@example.com',
                     'verified': True,
                     'primary': True,
                     },
                    {'email': 'secondverified@example.com',
                     'verified': True,
                     'primary': False,
                     },
                    {'email': 'first_not_verified@example.com',
                     'verified': False,
                     'primary': False,
                     },
                    {'email': 'thirdverified@example.com',
                     'verified': True,
                     'primary': False,
                     'created_by': 'dashboard',
                     }
                    ]
        got = this.mail_addresses.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        for addr in got:
            if addr.get('email') == 'thirdverified@example.com':
                del addr['created_ts']
        self.assertEqual(got, expected)

    def test_verify_existing_email_address(self):
        """ Verify an existing email address on the test user """
        this = self.mailuser
        _add_mail_to_user('first_not_verified@example.com', this)
        expected = [{'email': 'firstverified@example.com',
                     'verified': True,
                     'primary': True,
                     },
                    {'email': 'secondverified@example.com',
                     'verified': True,
                     'primary': False,
                     },
                    {'email': 'first_not_verified@example.com',
                     'verified': True,
                     'primary': False,
                     },
                    ]
        self.assertEqual(this.mail_addresses.to_list_of_dicts(), expected)

    def test_add_first_email_address(self):
        """ Add an email address to a test user that has none """
        userdoc = self.mailuser.to_dict()
        del userdoc['mailAliases']
        this = User(data = userdoc)
        _add_mail_to_user('first@example.com', this)
        expected = [{'email': 'first@example.com',
                     'verified': True,
                     'primary': True,
                     'created_by': 'dashboard',
                     }]
        got = this.mail_addresses.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        for addr in got:
            del addr['created_ts']
        self.assertEqual(got, expected)


class TestRemoveMailFromUsersInDb(LoggedInRequestTests):

    def test_remove_all_mail_addresses_in_db(self):
        """ Remove all e-mail addresses for all users in the db """
        for userdoc in self.userdb_new._get_all_docs():
            # Remove the addresses one by one until there are none left
            user = User(data = userdoc)
            addresses = user.mail_addresses.to_list()
            for this in addresses:
                expected = user.mail_addresses.count - 1
                new_user = _remove_mail_from_user(this.email, user)

                msg = 'Removing address {!s} from user {!s} did not result in address count == {!s}'.format(
                    this.email, user, expected)
                self.assertEqual(new_user.mail_addresses.count, expected, msg)

            # Remove the addresses individually, recreating the user from userdoc each time
            expected = len(addresses) - 1
            for this in addresses:
                user = User(data = userdoc)
                new_user = _remove_mail_from_user(this.email, user)
                msg = 'Removing address {!s} from user {!s} did not result in address count == {!s}'.format(
                    this.email, user, expected)
                self.assertEqual(new_user.mail_addresses.count, expected, msg)


class TestRemovePhoneFromUser(TestCase):

    def setUp(self):
        phoneuser = deepcopy(MOCKED_USER_STANDARD)
        phoneuser.update({
            'phone':
                [{'number': '1111',
                  'verified': True,
                  },
                 {'number': '2222',
                  'verified': True,
                  },
                 {'number': '0000',
                  'verified': False,
                  }],
        })
        self.phoneuser = User(data = phoneuser)

    def test_remove_primary_phone(self):
        """ Remove the primary address and expect the next verified one to be promoted to primary """
        this = _remove_phone_from_user('1111', self.phoneuser)
        expected = [{'number': '2222',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.phone_numbers.to_list_of_dicts(), expected)

    def test_remove_verified_phone(self):
        """ Remove a verified non-primary address """
        this = _remove_phone_from_user('2222', self.phoneuser)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.phone_numbers.to_list_of_dicts(), expected)

    def test_remove_nonverified_phone(self):
        """ Remove a non-verified address, although this user would not be found in reality """
        this = _remove_phone_from_user('0000', self.phoneuser)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     }]
        self.assertEqual(this.phone_numbers.to_list_of_dicts(), expected)

    def test_add_new_number(self):
        """ Add a new number to the test user """
        this = self.phoneuser
        _add_phone_to_user('3333', this)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     },
                    {'number': '3333',
                     'verified': True,
                     'primary': False,
                     #'created_by': 'dashboard',
                     }
                    ]
        got = this.phone_numbers.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        #for addr in got:
        #    if addr.get('number') == '3333':
        #        del addr['created_ts']
        self.assertEqual(got, expected)

    def test_verify_existing_number(self):
        """ Verify an existing number on the test user """
        this = self.phoneuser
        _add_phone_to_user('0000', this)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     },
                    {'number': '0000',
                     'verified': True,
                     'primary': False,
                     },
                    ]
        self.assertEqual(this.phone_numbers.to_list_of_dicts(), expected)

    def test_add_first_number(self):
        """ Add an number to a test user that has none """
        userdoc = self.phoneuser.to_dict()
        del userdoc['phone']
        this = User(data = userdoc)
        _add_phone_to_user('9999', this)
        expected = [{'number': '9999',
                     'verified': True,
                     'primary': True,
                     #'created_by': 'dashboard',
                     }]
        got = this.phone_numbers.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        #for addr in got:
        #    del addr['created_ts']
        self.assertEqual(got, expected)


class TestRemoveninFromUser(TestCase):

    def setUp(self):
        ninuser = deepcopy(MOCKED_USER_STANDARD)
        del ninuser['norEduPersonNIN']
        ninuser.update({
            'nins':
                [{'number': '1111',
                  'verified': True,
                  'primary': True,
                  },
                 {'number': '2222',
                  'verified': True,
                  },
                 {'number': '0000',
                  'verified': False,
                  }],
        })
        self.ninuser = User(data = ninuser)

    def test_remove_primary_nin(self):
        """ Remove the primary address and expect the next verified one to be promoted to primary """
        this = _remove_nin_from_user('1111', self.ninuser)
        expected = [{'number': '2222',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.nins.to_list_of_dicts(), expected)

    def test_remove_verified_nin(self):
        """ Remove a verified non-primary address """
        this = _remove_nin_from_user('2222', self.ninuser)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     }]
        self.assertEqual(this.nins.to_list_of_dicts(), expected)

    def test_remove_nonverified_nin(self):
        """ Remove a non-verified address, although this user would not be found in reality """
        this = _remove_nin_from_user('0000', self.ninuser)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     }]
        self.assertEqual(this.nins.to_list_of_dicts(), expected)

    def test_add_new_number(self):
        """ Add a new number to the test user """
        this = self.ninuser
        _add_nin_to_user('3333', this)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     },
                    {'number': '0000',
                     'verified': False,
                     'primary': False,
                     },
                    {'number': '3333',
                     'verified': True,
                     'primary': False,
                     'created_by': 'dashboard',
                     }
                    ]
        got = this.nins.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        for addr in got:
            if addr.get('number') == '3333':
                del addr['created_ts']
        self.assertEqual(got, expected)

    def test_verify_existing_number(self):
        """ Verify an existing number on the test user """
        this = self.ninuser
        now = datetime.datetime.utcnow()
        _add_nin_to_user('0000', this, created_ts = now)
        expected = [{'number': '1111',
                     'verified': True,
                     'primary': True,
                     },
                    {'number': '2222',
                     'verified': True,
                     'primary': False,
                     },
                    {'number': '0000',
                     'verified': True,
                     'primary': False,
                     'created_by': 'dashboard',
                     'created_ts': now,
                     },
                    ]
        self.assertEqual(this.nins.to_list_of_dicts(), expected)

    def test_add_first_number(self):
        """ Add an number to a test user that has none """
        userdoc = self.ninuser.to_dict()
        del userdoc['nins']
        this = User(data = userdoc)
        _add_nin_to_user('9999', this)
        expected = [{'number': '9999',
                     'verified': True,
                     'primary': True,
                     'created_by': 'dashboard',
                     }]
        got = this.nins.to_list_of_dicts()
        # remove the 'created_ts' from the new entry
        for addr in got:
            del addr['created_ts']
        self.assertEqual(got, expected)
