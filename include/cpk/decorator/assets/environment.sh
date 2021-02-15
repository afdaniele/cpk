#!/bin/bash

# source entrypoint if it hasn't been done
if [ "${CPK_ENTRYPOINT_SOURCED}" != "1" ]; then
    source ${CPK_INSTALL_DIR}/entrypoint.sh
fi

cpk-utils-terminate() {
    # send SIGINT signal to monitored process
    kill -INT $(pgrep -P $$) 2>/dev/null
}

cpk-utils-register-signals() {
    trap cpk-utils-terminate SIGINT
    trap cpk-utils-terminate SIGTERM
}

cpk-utils-join() {
    # wait for all the processes in the background to terminate
    set +e
    wait &>/dev/null
    set -e
}

cpk-launcher-init() {
    set -e
    # register signal handlers
    cpk-utils-register-signals
    if [ "$1" != "--quiet" ]; then
        echo "==> Launching app..."
    fi
}

cpk-launcher-join() {
    # wait for the process to end
    cpk-utils-join
    # wait for stdout to flush, then announce app termination
    sleep 0.5
    if [ "$1" != "--quiet" ]; then
        printf "<== App terminated!\n"
    fi
}

cpk-exec() {
    cmd="$@"
    cpk-debug "Running command: ${cmd}"
    cmd="${cmd%&} &"
    eval "${cmd}"
}
