import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'eduid_am',
    'pymongo==2.5.1',
    'pyramid==1.4',
    'pyramid_jinja2==1.6',
    'pyramid_debugtoolbar==1.0.4',

]

if sys.version_info[0] < 3:
    # Babel does not work with Python 3
    requires.append('Babel==0.9.6')


test_requires = [
    'WebTest==1.4.3',
]


docs_extras = [
    'Sphinx==1.1.3'
]


testing_extras = test_requires + [
    'nose==1.2.1',
    'coverage==3.6',
]


setup(name='eduid-dashboard',
      version='0.0',
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
      extras_require={
          'testing': testing_extras,
          'docs': docs_extras,
      },
      test_suite="eduiddashboard",
      entry_points="""\
      [paste.app_factory]
      main = eduiddashboard:main
      """,
      )
