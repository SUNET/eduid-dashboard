Installation
============

Minimum requirements
--------------------
eduID Dashboard is a Python web application so you will need a Python
interpreter for running it. It has been tested with Python 2.7 and
Python 3.3 so either one should work fine. However we recommend
sticking with Python 2.7 since not all the Python dependencies for
eduID Dashboard works with Python 3.

This guide will document the process of installing eduID Dashboard
in a Linux distribution, either a Debian or Redhat based one. The
authors do not have a Windows box available to test and document its
installation.

In all Linux modern distributions Python 2.7 is installed by default
so you will not need to do anything special at this point.

The `eduid-am (eduID Attribute Manager) <https://github.com/SUNET/eduid-dashboard>`_
application is required too. So it's recommended to install it before start to
install eduID Dashboard. eduid-am can be installed in another host.

You need to install the follow packages too:

Deb based example:

.. code-block:: none

    $ sudo apt-get install xmlsec1 libxmlsec1 libxmlsec1-openssl libswig
    $ sudo apt-get install python-m2crypto


You need a MongoDB instance. You can install the mongodb-server in the same
server where is installed the eduid-dashboard or just in another server.

.. code-block:: none

    $ sudo apt-get install mongodb-server


Installing virtualenv
---------------------
In Python it is considered best practice to install your applications
inside virtual environments. To do so you will need to install the
virtualenv package for your Linux distribution:

Deb based example:

.. code-block:: none

   $ sudo apt-get install python-setuptools python-virtualenv

Rpm based example:

.. code-block:: none

   $ sudo yum install python-setuptools
   $ sudo easy_install virtualenv

Once the virtualenv package has been installed a new virtual environment
can be created with a very simple command:

.. code-block:: none

   $ sudo virtualenv /opt/eduid-dashboard
   New python executable in /opt/eduid-dashboard/bin/python
   Installing setuptools............done.
   Installing pip...............done.

In order to be useful the virtual environment needs to be activated:

.. code-block:: none

   $ source /opt/eduid-dashboard/bin/activate
   (eduid-signup)$



The pypi version of m2crypto has some bugs, so we are going to use the official
from distribution `link to stackoverflow
<http://stackoverflow.com/questions/10547332/install-m2crypto-on-a-virtualenv-without-system-packages>`_.
To use that in our virtualenv, we need to do this link:

.. code-block:: none

   $ sudo rm -rf /opt/eduid-dashboard/lib/python2.7/site-packages/M2Crypto
   $ sudo ln -s /usr/lib/python2.7/dist-packages/M2Crypto/
     /opt/eduid-dashboard/lib/python2.7/site-packages/


Installing eduID Dashboard
------------------------
After the virtualenv is activated it is time to install eduID Dashboard itself.
You can choose between installing a development version or a stable version.

Stable version
""""""""""""""
Installing a stable version is really easy, all you have to do is execute the
following command and have a coffee while it downloads the application and all
its dependencies:

.. code-block:: none

   (eduid-signup)$ easy_install eduid_dashboard

Development version
"""""""""""""""""""
To install a development version first the code needs to be checked out from
the Git repository at Github.com:

.. code-block:: text

   (eduid-signup)$ cd /opt/eduid-dashboard
   (eduid-signup)$ git clone git://github.com/SUNET/eduid-dashboard.git
   Cloning into 'eduid-signup'...
   remote: Counting objects: 424, done.
   remote: Compressing objects: 100% (259/259), done.
   remote: Total 424 (delta 235), reused 315 (delta 126)
   Receiving objects: 100% (424/424), 245.39 KiB | 70 KiB/s, done.
   Resolving deltas: 100% (235/235), done.

Then it can be installed in development mode, which will install it and all
its dependencies in the virtualenv:

.. code-block:: text

   (eduid-signup)$ cd /opt/eduid-dashboard/eduid-dashboard
   (eduid-signup)$ python setup.py develop

Database setup
--------------
eduID Sign Up stores the information about registered users in a MongoDB
database so you need it installed in the same machine or in other box that
is accessible from the one you installed eduID Sign Up in.

Deb based example:

.. code-block:: text

   $ sudo apt-get install mongodb mongodb-server

Rpm based example:

.. code-block:: text

   $ sudo yum install mongodb mongodb-server

Now it is time to start the database server and configure it to start at boot
time.

Deb based example:

.. code-block:: text

   $ sudo service mongodb start
   $ sudo update-rc.d mongodb defaults

Rpm based example:

.. code-block:: text

   $ sudo systemctl start mongod.service
   $ sudo systemctl enable mongod.service


Saml2 setup
-----------

We need a Saml2 IDP instance up, you must use `eduid-IdP
<https://github.com/SUNET/eduid-IdP>`_ but you can use a simplesamlphp instance
if you have one.

SSL Certs
'''''''''

You need HTTP SSL certificates (key and cert). According to saml2_settings.py
from config-templates, the best place for put the certificates is in a
directory called certs in the directory where is the saml2_settings.py file.

You can use a verified SSL certificates from Verisign or RapidSSL.

If you don't have any certs, you can create self-signed certs for development
or testing environments. You must have installed openssl command, and then, you
can follow the follow lines to get your certs.

Remember set the correct domain name in the CN (common name) property:

.. code-block:: none

    $ sudo mkdir /opt/eduid-dashboard/certs
    $ cd /opt/eduid-dashboard/certs
    $ openssl genrsa -out server.key 2048
    $ openssl req -new -key server.key -out server.csr
    $ openssl x509 -req -days 3650 -in server.csr -signkey server.key -out server.crt


Saml2 Settings file
'''''''''''''''''''

The saml2 need another settings file. There are a template in
`config-templates`. You need to setup your metadata, urls, and IDP url.

.. code-block:: none

    $ cd /opt/eduid-dashboard/
    $ cp /opt/eduid-dashboard/eduid-dashboard/config-templates/saml2_settings.py \
         /opt/eduid-dashboard

Testing the application
-----------------------
Once everything is installed, the application can be started but first
you need to write a configuration file. Luckily, there are several
example configuration files in the `config-templates` directory ready
to be used. For example, the `development.ini` is a good starting point
if you want to test or develop the application:

.. code-block:: none

   $ cd /opt/eduid-dashboard/
   $ cp config-templates/development.ini myconfig.ini

It is important to activate the virtualenv before running the server:

.. code-block:: none

   $ source /opt/eduid-signup/bin/activate
   (eduid-signup)$ pserver myconfig.ini
   Starting server in PID 16756.
   serving on http://0.0.0.0:6544

Now you can open the link http://0.0.0.0:6543 in your browser and test
the application.

The `pserve` command will use the `Waitress` WSGI server which is a very
capable server and also very handy for development.

The next thing you should do is learn about all the configuration options
and other WSGI server choices for production.
