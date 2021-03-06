import os
import sys

from setuptools import setup, find_packages

try:
    from babel.messages import frontend as babel
except ImportError:
    print "Babel is not installed, you can't localize this package"
    cmdclass = {}
else:
    cmdclass = {
        'compile_catalog': babel.compile_catalog,
        'extract_messages': babel.extract_messages,
        'init_catalog': babel.init_catalog,
        'update_catalog': babel.update_catalog
    }


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

version = '0.5.1b15'

requires = [
    'eduid_am >= 0.6.0',
    'eduid_msg >= 0.9.0',
    'vccs_client >= 0.4.4',
    'eduid_lookup_mobile >= 0.0.4',
    'eduid_userdb >= 0.2.6b1',
    'eduid-common[nodeps] >= 0.3.0b2',
    'six >= 1.11.0',
    'Flask>=0.10.1,<0.12',  # Dependency for eduid-common
    'redis >= 2.10.5',
    'PyNaCl >= 1.0.1',
    'pysaml2 == 4.0.3rc1',
    'pyramid==1.4.1',
    'pyramid_jinja2==1.6',
    'jinja2<2.9',  # Templates breaks with jinja2 2.9
    'pyramid_debugtoolbar==1.0.4',
    'pyramid_deform==0.2',
    'pyramid_mailer==0.11',
    'pyramid_tm==1.0.2',
    'colander==1.0b1',
    'deform==2.0a2',
    'deform_bootstrap==0.2.9',
    'pycountry==1.2',
    'eventlet==0.14.0',
    'gunicorn==18.0',
    'pwgen==0.4',
    'zxcvbn==1.0',
    'pytz',
    'statsd==3.2.1',
    'markupsafe>=0.23',
    'bleach>=1.4.2',
    'requests>=2.8.1',
]

if sys.version_info[0] < 3:
    # Babel does not work with Python 3
    requires.append('Babel==1.3')
    requires.append('lingua==1.5')


test_requires = [
    'WebTest==2.0.18',
    'mock',
    'eduid_dashboard_amp',
]


docs_extras = [
    'Sphinx==1.1.3'
]


testing_extras = test_requires + [
    'nose',
    'coverage',
    'nosexcover',
]

waitress_extras = requires + [
    'waitress==0.8.2',
]

setup(name='eduid-dashboard',
      version=version,
      description='eduid-dashboard',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pylons",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
      ],
      author='NORDUnet A/S',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      cmdclass=cmdclass,
      extras_require={
          'testing': testing_extras,
          'docs': docs_extras,
          'waitress': waitress_extras,
      },
      test_suite="eduiddashboard",
      entry_points="""\
      [paste.app_factory]
      main = eduiddashboard:main
      [console_scripts]
      fallback_letter_proofing=eduiddashboard.scripts.fallback_letter_proofing:letter_proof_user
      """,
      )
