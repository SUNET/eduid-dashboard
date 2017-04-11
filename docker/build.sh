#!/bin/bash
#
# Run build commands that should never be docker-build cached
#

set -e
set -x

PYPI="https://pypi.sunet.se/simple/"
ping -c 1 -q pypiserver.docker && PYPI="http://pypiserver.docker:8080/simple/"

echo "#############################################################"
echo "$0: Using PyPi URL ${PYPI}"
echo "#############################################################"

/opt/eduid/bin/pip install --pre -i ${PYPI} /src/eduid-dashboard

/opt/eduid/bin/pip freeze
