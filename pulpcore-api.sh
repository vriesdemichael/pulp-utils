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



$BIN_DIR/gunicorn pulpcore.app.wsgi:application --bind '127.0.0.1:24817' --worker-class 'aiohttp.GunicornWebWorker' --workers 1 --access-logfile - --access-logformat 'pulp [%({correlation-id}o)s]: %(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'


