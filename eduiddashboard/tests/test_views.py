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
        from eduiddashboard.views import home
        request = testing.DummyRequest()
        response = home({}, request)
        self.assertEqual(response, {
            'user': None
        })

        request = testing.DummyRequest()
        request.session = {
            'user': {
                'email': 'email@example.com'
            },
        }

        response = home({}, request)
        self.assertEqual(response, request.session)
