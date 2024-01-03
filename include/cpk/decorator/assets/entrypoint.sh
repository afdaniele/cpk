#!/bin/bash

# if anything weird happens from now on, STOP
set -e

cpk-debug() {
    if [ "${DEBUG:-0}" = "1" ]; then
        echo "D: $1"
    fi
}

cpk-info() {
    echo "I: $1"
}

cpk-warn() {
    echo "W: $1"
}

cpk-error() {
    echo "E: $1"
}

cpk-debug-show-command-on() {
    if [ "${DEBUG:-0}" = "1" ]; then
        set -x
    fi
}

cpk-debug-show-command-off() {
    { set +x; } 2>/dev/null
}

cpk-debug "=> Entrypoint"

ALL_PROJECTS=$(find "${CPK_SOURCE_DIR}/" -path \*/cpk/self.yaml -type f -printf "%T@ %p\n" | sort -n -r | awk '{print $2}')

cpk-configure-entrypoint.d() {
    # source all the entrypoint.d scripts provided by the projects
    for candidate_project in ${ALL_PROJECTS}; do
        project_dir="$(realpath $(dirname "${candidate_project}")/../)"
        candidate_entrypointd_dir="${project_dir}/assets/entrypoint.d"
        if [ -d "${candidate_entrypointd_dir}" ]; then
            cpk-debug "   > Entering ${candidate_entrypointd_dir}/"
            for f in $(find "${candidate_entrypointd_dir}" -mindepth 1 -maxdepth 1 -type f -name "*.sh" | sort); do
                cpk-debug "     > Sourcing ${f}"
                source ${f}
                cpk-debug "     < Sourced  ${f}"
            done
            cpk-debug "   < Exiting ${candidate_entrypointd_dir}/"
        fi
    done
}

cpk-configure-user() {
    # impersonate UID
    if [ "${IMPERSONATE_UID:-}" != "" ]; then
        cpk-debug "Impersonating user with UID: ${IMPERSONATE_UID}"
        usermod -u ${IMPERSONATE_UID} ${CPK_USER_NAME}
        export CPK_USER_UID=${IMPERSONATE_UID}
    fi
    # impersonate GID
    if [ "${IMPERSONATE_GID:-}" != "" ]; then
        cpk-debug "Impersonating group with GID: ${IMPERSONATE_GID}"
        groupmod -g ${IMPERSONATE_GID} ${CPK_USER_NAME} || :
        export CPK_GROUP_GID=${IMPERSONATE_GID}
    fi
}


if [ "${CPK_ENTRYPOINT_EXECUTED:-0}" != "1" ]; then
    # configure
    cpk-debug " > Setting up user..."
    cpk-configure-user
    cpk-debug " < Done!"

    cpk-debug " > Setting up entrypoint.d..."
    cpk-configure-entrypoint.d
    cpk-debug " < Done!"

    # mark this file as executed
    CPK_ENTRYPOINT_EXECUTED=1
    export CPK_ENTRYPOINT_EXECUTED
fi

# if anything weird happens from now on, CONTINUE
set +e

# exit if this file is just being sourced
if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    cpk-debug "<= Entrypoint"
    return
fi

# reuse CPK_LAUNCHER as CMD if the var is set and the first argument is `--`
if [ ${#CPK_LAUNCHER} -gt 0 ] && [ "$1" == "--" ]; then
    shift
    # exec launcher
    cpk-debug "<= Entrypoint"
    cpk-debug "=> Executing launcher '${CPK_LAUNCHER}'..."
    if [[ "${CPK_SUPERUSER:-0}" == "1" ]]; then
        cpk-debug-show-command-on
        exec bash -c "launcher-$CPK_LAUNCHER $*"
    else
        cpk-debug-show-command-on
        exec sudo \
            --set-home \
            --preserve-env \
            --user ${CPK_USER_NAME} \
                LD_LIBRARY_PATH=$LD_LIBRARY_PATH \
                PYTHONPATH=$PYTHONPATH \
                PATH=$PATH \
                BASH_ENV=$BASH_ENV \
                bash -c "launcher-$CPK_LAUNCHER $*"
    fi
else
    # just exec the given arguments
    cpk-debug "<= Entrypoint"
    cpk-debug "=> Executing command '$*'..."
    if [[ "${CPK_SUPERUSER:-0}" == "1" ]]; then
        cpk-debug-show-command-on
        exec "$@"
    else
        cpk-debug-show-command-on
        exec sudo \
            --set-home \
            --preserve-env \
            --user ${CPK_USER_NAME} \
                LD_LIBRARY_PATH=$LD_LIBRARY_PATH \
                PYTHONPATH=$PYTHONPATH \
                PATH=$PATH \
                BASH_ENV=$BASH_ENV \
                "$@"
    fi
fi