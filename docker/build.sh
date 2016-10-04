#!/bin/bash
#
# Run build commands that should never be docker-build cached
#

set -e
set -x

/opt/eduid/bin/pip install /src/eduid-dashboard

/opt/eduid/bin/pip freeze
