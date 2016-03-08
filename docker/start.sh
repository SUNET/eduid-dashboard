#!/bin/sh

set -e
set -x

. /opt/eduid/bin/activate

# These could be set from Puppet if multiple instances are deployed
eduid_name=${eduid_name-'eduid-dashboard'}
base_dir=${base_dir-"/opt/eduid/${eduid_name}"}
# These *can* be set from Puppet, but are less expected to...
cfg_dir=${cfg_dir-"${base_dir}/etc"}
log_dir=${log_dir-'/var/log/eduid'}
state_dir=${state_dir-"${base_dir}/run"}
metadata=${metadata-"${state_dir}/metadata.xml"}
ini=${ini-"${cfg_dir}/${eduid_name}.ini"}
pysaml2_settings=${pysaml2_settings-"${cfg_dir}/dashboard_pysaml2_settings.py"}

chown eduid: "${log_dir}" "${state_dir}"

# || true to not fail on read-only cfg_dir
chgrp eduid "${ini}" || true
chmod 640 "${ini}" || true

pserve_args=""
if [ -f "/opt/eduid/src/${eduid_name}/setup.py" ]; then
    # developer mode, restart on code changes
    pserve_args="--reload --monitor-restart"
fi

# nice to have in docker run output, to check what
# version of something is actually running.
/opt/eduid/bin/pip freeze

if [ ! -s "${metadata}" ]; then
    # Create file with local SP metadata
    cd "${cfg_dir}" && \
	/opt/eduid/bin/make_metadata.py "${pysaml2_settings}" | \
	xmllint --format - > "${metadata}"
fi

echo "$0: pserving ${ini}"
exec start-stop-daemon --start -c eduid:eduid --exec \
     /opt/eduid/bin/pserve -- "${ini}" \
     --pid-file "${state_dir}/${eduid-name}.pid" \
     --log-file "${log_dir}/${eduid_name}.log" \
    $pserve_args
