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
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

version = '0.3.5'

requires = [
    'eduid_am>=0.5.1',
    'eduid_msg>=0.8.3',
    'pymongo==2.6.3',
    'pyramid==1.4.1',
    'pyramid_jinja2==1.6',
    'pyramid_debugtoolbar==1.0.4',
    'pyramid_beaker==0.7',
    'pyramid_deform==0.2',
    'pyramid_mailer==0.11',
    'pyramid_tm==0.7',
    'colander==1.0b1',
    'deform==0.9.8',
    'deform_bootstrap==0.2.9',
    'pysaml2==1.2.0beta2',
    'pycountry==1.2',
    'eventlet==0.14.0',
    'gunicorn==18.0',
    'vccs_client==0.4.1',
    'pwgen==0.4',
    'zxcvbn==1.0',
    'pytz'
]

if sys.version_info[0] < 3:
    # Babel does not work with Python 3
    requires.append('Babel==1.3')
    requires.append('lingua==1.5')


test_requires = [
    'WebTest==1.4.3',
    'mock==1.0.1',
]


docs_extras = [
    'Sphinx==1.1.3'
]


testing_extras = test_requires + [
    'nose==1.2.1',
    'coverage==3.6',
    'nosexcover==1.0.8',
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
      """,
      )
