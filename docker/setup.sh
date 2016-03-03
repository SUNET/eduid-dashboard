#!/bin/bash
#
# Install all requirements
#

set -e
set -x

#  libffi-dev         # needed by pysaml2
#  libssl-dev         # needed by pysaml2

apt-get update
apt-get -y dist-upgrade
apt-get -y install \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    xmlsec1 \
    libxml2-utils \
    libffi-dev \
    libssl-dev

apt-get clean
rm -rf /var/lib/apt/lists/*

PYPI="https://pypi.nordu.net/simple/"
ping -c 1 -q pypiserver.docker && PYPI="http://pypiserver.docker:8080/simple/"

echo "#############################################################"
echo "$0: Using PyPi URL ${PYPI}"
echo "#############################################################"
/opt/eduid/bin/pip install --pre -i ${PYPI} eduid-am
/opt/eduid/bin/pip install --pre -i ${PYPI} eduid-lookup-mobile
/opt/eduid/bin/pip install       -i ${PYPI} raven

/opt/eduid/bin/pip freeze
