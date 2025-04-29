#!/bin/bash
set -e -u

# Function to wait for unoserver to start
wait_for_unoserver() {
    echo "Waiting for unoserver to start on port 2003..."
    while ! netstat -tln | grep -q 2003; do
        sleep 1
    done
    echo "unoserver started."
}

maybe_start_rest_server() {
    if [ $START_REST_API = "true" ]; then
        echo "Rest server available at port 8000"
        export SUPERVISOR_INTERACTIVE_CONF='/rest-service/supervisord.conf'
        supervisord -c "$SUPERVISOR_INTERACTIVE_CONF"
    fi;
}

export PS1='\u@\h:\w\$ '

echo -n "using: $(libreoffice --version), unoserver at version $VERSION_UNOSERVER"

if [ $START_REST_API = "true" ]; then
    echo ", and starting REST API service"
    if [ -z $REST_API_KEY ]; then
        echo "WARNING: REST_API_KEY not provided, dont expose the container to the internet"
    fi;
else
    echo ""
fi;

# if tty then assume that container is interactive
if [ ! -t 0 ]; then
    echo "Running unoserver-docker in non-interactive."
    echo "For interactive mode use '-it', e.g. 'docker run -v /tmp:/data -it unoserver/unoserver-docker'."

    maybe_start_rest_server
    
    unoserver --interface 0.0.0.0
    # # run supervisord in foreground
    # supervisord -c "$SUPERVISOR_NON_INTERACTIVE_CONF"
else
    echo "Running unoserver-docker in interactive mode."
    echo "For non-interactive mode omit '-it', e.g. 'docker run -p 2003:2003 unoserver/unoserver-docker'."

    # default parameters for supervisord
    export SUPERVISOR_INTERACTIVE_CONF='/supervisor/conf/interactive/supervisord.conf'
    export UNIX_HTTP_SERVER_PASSWORD=${UNIX_HTTP_SERVER_PASSWORD:-$(cat /proc/sys/kernel/random/uuid)}

    # run supervisord as detached
    supervisord -c "$SUPERVISOR_INTERACTIVE_CONF"

    # wait until unoserver started and listens on port 2002.
    wait_for_unoserver

    maybe_start_rest_server
    
    # if commands have been passed to container run them and exit, else start bash
    if [[ $# -gt 0 ]]; then
        eval "$@"
    else
        /bin/bash
    fi
fi
