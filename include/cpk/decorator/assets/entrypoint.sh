#!/bin/bash

# if anything weird happens from now on, STOP
set -e

cpk-debug() {
    if [ "${DEBUG:-0}" = "1" ]; then
        echo "DEBUG: $1"
    fi
}

cpk-debug "==> Entrypoint"

cpk-configure-python() {
    # make user libraries discoverable
    PYTHON_VERSION=$(python3 -c 'import sys; print(str(sys.version_info[0])+"."+str(sys.version_info[1]))')
    PYTHONPATH=/usr/local/lib/python${PYTHON_VERSION}/dist-packages:${PYTHONPATH}

    # make user code discoverable by python
    for candidate_project in $(find "${CPK_SOURCE_DIR}/" -name project.cpk -type f -printf "%T@ %p\n" | sort -n -r | awk '{print $2}'); do
        project_dir="$(dirname "${candidate_project}")"
        project_name="$(realpath --relative-to="${CPK_SOURCE_DIR}" "${project_dir}")"
        candidate_packages_dir="${project_dir}/packages"
        cpk-debug " > Setting up Python for project '${project_name}'..."
        if [ -d "${candidate_packages_dir}" ]; then
            cpk-debug "   > Adding '${candidate_packages_dir}' to PYTHONPATH."
            PYTHONPATH="${candidate_packages_dir}:${PYTHONPATH}"
        else
            cpk-debug "   ! Directory '${candidate_packages_dir}' not found."
        fi
    done

    # export
    export PYTHONPATH
}

cpk-configure-projects() {
    # source projects the same order they were created
    for candidate_project in $(find "${CPK_SOURCE_DIR}/" -name project.cpk -type f -printf "%T@ %p\n" | sort -n -r | awk '{print $2}'); do
        project_dir="$(dirname "${candidate_project}")"
        project_name="$(realpath --relative-to="${CPK_SOURCE_DIR}" "${project_dir}")"
        candidate_setup_file="${project_dir}/setup.sh"
        if [ -f "${candidate_setup_file}" ]; then
            cpk-debug " > Setting up project '${project_name}'..."
            cpk-debug "   > Sourcing file '${candidate_setup_file}'..."
            set +eu
            source "${candidate_setup_file}"
            set -eu
            cpk-debug "   < File '${candidate_setup_file}' sourced!"
        fi
    done
}

if [ "${CPK_ENTRYPOINT_SOURCED:-0}" != "1" ]; then
    # configure
    cpk-debug "=> Setting up PYTHONPATH..."
    cpk-configure-python
    cpk-debug "<= Done!"

    cpk-debug "=> Setting up projects..."
    cpk-configure-projects
    cpk-debug "<= Done!"

    # mark this file as sourced
    CPK_ENTRYPOINT_SOURCED=1
    export CPK_ENTRYPOINT_SOURCED
fi

# if anything weird happens from now on, CONTINUE
set +e

# exit if this file is just being sourced
if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    cpk-debug "<= File ${BASH_SOURCE[0]} sourced!"
    cpk-debug "<== Entrypoint"
    return
fi

# reuse CPK_LAUNCHER as CMD if the var is set and the first argument is `--`
if [ ${#CPK_LAUNCHER} -gt 0 ] && [ "$1" == "--" ]; then
    shift
    # exec launcher
    cpk-debug "=> Executing launcher '${CPK_LAUNCHER}'"
    cpk-debug "<== Entrypoint"
    exec bash -c "launcher-$CPK_LAUNCHER $*"
else
    # just exec the given arguments
    cpk-debug "=> Executing command '$*'"
    cpk-debug "<== Entrypoint"
    exec "$@"
fi
