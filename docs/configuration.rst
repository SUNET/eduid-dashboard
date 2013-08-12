Configuration
=============

eduID Dashboard read its configuration options from two different sources:

- A configuration file with a INI syntax
- Environment variables. Not all configuration options support this.

If one option is defined both in the configuration file and the environment
variable, eduID Dashboard will use the environment variable.

In the source distribution there are two configuration templates, one
for development and other for production purposes. It is recommended that
you copy one of them and edit it instead of writing a configuration file
from scratch. Do not edit the templates themselves as that will make
upgrading more difficult.

The following is the list of available options.

Authentication
--------------

eduID Dashboard uses a secret value to sign the authentication ticket
cookie, which is used to keep track of the authentication status of the
current user.

It is extremely important that **this value is kept secret**. This
is a required value with an empty default value. This means that
you need to set it before running the server. The
:file:`development.ini` template has a value of ``1234`` for this
option so you can get your server running as fast as possible
without worrying about these things.

.. code-block:: ini

   auth_tk_secret = 7qankk6hu55lxlacyiw70js6cxeaw9l6

In this example, the auth_tk_secret value has been generated
with the following command in a Unix shell:

.. code-block:: text

   $ tr -c -d '0123456789abcdefghijklmnopqrstuvwxyz' </dev/urandom | dd bs=32 count=1 2>/dev/null;echo

You can also set this option with an environment variable:

.. code-block:: bash

   $ export AUTH_TK_SECRET=7qankk6hu55lxlacyiw70js6cxeaw9l6

Available languages
-------------------

This option defines the set of available languages that eduID Dashboard will
use for internationalization purposes. The value is a space separated list
of iso codes:

.. code-block:: ini

   available_languages = en es

The default value for this option is ``en es``, which means there is support
for English and Spanish.

As of this writing only English and Spanish translation of UI text messages
are available. With this configuration option you can restrict the set of
available languages but if you add new languages to it, their translation
catalogs will not be generated magically.

Broker
------

eduID Dashboard uses Celery to send messages to the eduID Attribute Manager.
In order to accomplish this task it needs a message broker to deliver those
messages.

This option allows you to customize the broker location. The syntax is defined
in Celery reference documentation as the
`BROKER_URL format <http://docs.celeryproject.org/en/latest/configuration.html#broker-url>`_

.. code-block:: ini

   broker_url = amqp://

You can also set this option with an environment variable:

.. code-block:: none

   $ export BROKER_URL=amqp://

The default value for this option is ``amqp://`` which is a good value
for connecting to a basic RabbitMQ server.

Database
--------
This option allows you to customize the database location and other settings.

The syntax is defined in MongoDB reference documentation as the
`Connection String URI Format <http://docs.mongodb.org/manual/reference/connection-string/>`_

.. code-block:: ini

   mongo_uri = mongodb://localhost:27017/eduid_dashboard

You can also set this option with an environment variable:

.. code-block:: none

   $ export MONGO_URI=mongodb://localhost:27017/eduid_dashboard

The default value for this option is ``mongodb://localhost:27017/eduid_signup``

Email
-----
The application uses an SMTP server to send verification emails when users
register in the system.

eduID Dashboard uses the library
`pyramid_mailer <https://pypi.python.org/pypi/pyramid_mailer>`_ so you can
check the available options at
`pyramid_mailer documentation <http://docs.pylonsproject.org/projects/pyramid_mailer/en/latest/#configuration>`_

Some of the most common used are:

.. code-block:: ini

   mail.host = localhost
   mail.port = 25
   mail_default_sender = no-reply@localhost.localdomain


