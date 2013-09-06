import unittest
from pyramid import testing
from pyramid.i18n import TranslationStringFactory

_ = TranslationStringFactory('eduiddashboard')


class ViewTests(unittest.TestCase):

    def setUp(self):
        testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        from eduiddashboard.views.portal import home
        request = testing.DummyRequest()

        request.session = {
            'user': {
                'mail': 'email@example.com'
            },
        }

        response = home({}, request)
        self.assertEqual(response['mail'], 'email@example.com')
