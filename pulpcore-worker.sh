#!/bin/bash
if [ `whoami` != 'pulp' ]
    then 
        echo "You must run this script as user pulp"
        exit 1
fi

BIN_DIR="/opt/pulp/venv/bin"
cd $BIN_DIR
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings
export PULP_SETTINGS="/opt/pulp/settings.py"
export PATH="$BINDIR:$PATH"



$BIN_DIR/rq worker -w pulpcore.tasking.worker.PulpWorker -c 'pulpcore.rqconfig' --disable-job-desc-logging


