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

cpk-debug "=> Entrypoint"

ALL_PROJECTS=$(find "${CPK_SOURCE_DIR}/" -path \*/cpk/self.yaml -type f -printf "%T@ %p\n" | sort -n -r | awk '{print $2}')

cpk-configure-python() {
    # make user libraries discoverable
    PYTHON_VERSION=$(python3 -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')
    PYTHONPATH=/usr/local/lib/python${PYTHON_VERSION}/dist-packages:${PYTHONPATH}

    # make user code discoverable by python
    for candidate_project in ${ALL_PROJECTS}; do
        project_dir="$(realpath $(dirname "${candidate_project}")/../)"
        project_name="$(realpath --relative-to="${CPK_SOURCE_DIR}" "${project_dir}")"
        candidate_packages_dir="${project_dir}/packages"
        cpk-debug "   > Setting up Python for project '${project_name}'..."
        if [ -d "${candidate_packages_dir}" ]; then
            cpk-debug "     > Adding '${candidate_packages_dir}' to PYTHONPATH."
            PYTHONPATH="${candidate_packages_dir}:${PYTHONPATH}"
        else
            cpk-debug "     ! Directory '${candidate_packages_dir}' not found."
        fi
    done

    # export
    export PYTHONPATH
}

cpk-configure-entrypoint.d() {
    # source all the entrypoint.d scripts provided by the projects
    for candidate_project in ${ALL_PROJECTS}; do
        project_dir="$(realpath $(dirname "${candidate_project}")/../)"
        candidate_entrypointd_dir="${project_dir}/assets/entrypoint.d"
        if [ -d "${candidate_entrypointd_dir}" ]; then
            cpk-debug "   > Entering ${candidate_entrypointd_dir}/"
            for f in $(find "${candidate_entrypointd_dir}" -mindepth 1 -maxdepth 1 -type f -name "*.sh"); do
                cpk-debug "     > Sourcing ${f}"
                source ${f}
                cpk-debug "     < Sourced ${f}"
            done
            cpk-debug "   < Exiting ${candidate_entrypointd_dir}/"
        fi
    done
}

cpk-configure-libraries() {
    # superimpose libraries provided by the dtprojects
    for candidate_project in ${ALL_PROJECTS}; do
        project_dir="$(realpath $(dirname "${candidate_project}")/../)"
        candidate_libraries_dir="${project_dir}/libraries"
        if [ -d "${candidate_libraries_dir}" ]; then
            cpk-debug "   > Processing ${candidate_libraries_dir}/"
            for lib in $(find "${candidate_libraries_dir}" -mindepth 1 -maxdepth 1 -type d); do
                candidate_library_setup_py="${lib}/setup.py"
                if [ -f "${candidate_library_setup_py}" ]; then
                    cpk-debug "     > Found library in ${lib}"
                    python3 -m pip install --no-dependencies -e "${lib}" > /dev/null
                    cpk-info "     < Loaded library: $(basename ${lib})\t(from: ${lib})"
                fi
            done
            cpk-debug "   < Exiting ${candidate_libraries_dir}/"
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




if [ "${CPK_ENTRYPOINT_SOURCED:-0}" != "1" ]; then
    # configure
    cpk-debug " > Setting up user..."
    cpk-configure-user
    cpk-debug " < Done!"

    cpk-debug " > Setting up PYTHONPATH..."
    cpk-configure-python
    cpk-debug " < Done!"

    cpk-debug " > Setting up libraries..."
    cpk-configure-libraries
    cpk-debug " < Done!"

    cpk-debug " > Setting up entrypoint.d..."
    cpk-configure-entrypoint.d
    cpk-debug " < Done!"

    # mark this file as sourced
    CPK_ENTRYPOINT_SOURCED=1
    export CPK_ENTRYPOINT_SOURCED
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
    exec bash -c "launcher-$CPK_LAUNCHER $*"
else
    # just exec the given arguments
    cpk-debug "<= Entrypoint"
    cpk-debug "=> Executing command '$*'..."
    exec "$@"
fi
