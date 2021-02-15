#!/bin/bash

echo "==> Entrypoint"

# if anything weird happens from now on, STOP
set -e

cpk-debug() {
    if [ "${DEBUG}" = "1" ]; then
        echo "DEBUG: $1"
    fi
}

cpk-configure-python() {
    # make user libraries discoverable
    PYTHONPATH=/usr/local/lib/python3/dist-packages:${PYTHONPATH}
    PYTHONPATH=/usr/local/lib/python3.8/dist-packages:${PYTHONPATH}

    # make user code discoverable by python
    for d in $(find "${CPK_SOURCE_DIR}" -mindepth 1 -maxdepth 1 -type d); do
        cpk-debug " > Setting up Python for project $(basename $d)..."
        candidate_dir="${d}/packages"
        if [ -d "${candidate_dir}" ]; then
            cpk-debug "   > Adding ${candidate_dir} to PYTHONPATH."
            PYTHONPATH="${candidate_dir}:${PYTHONPATH}"
        else
            cpk-debug "   ! Directory ${candidate_dir} not found."
        fi
    done

    # export
    export PYTHONPATH
}

cpk-configure-projects() {
    # source projects the same order they were created
    for candidate_setup_file in $(find ${CPK_SOURCE_DIR}/*/setup.sh -type f -printf "%T@ %p\n" | sort -n | awk '{print $2}'); do
        project_name="$(basename $(dirname ${candidate_setup_file}))"
        cpk-debug " > Setting up project ${project_name}..."
        cpk-debug "   > Sourcing file ${candidate_setup_file}..."
        source "${candidate_setup_file}"
        cpk-debug "   < File ${candidate_setup_file} sourced!"
    done
}

# configure
cpk-debug "=> Setting up PYTHONPATH..."
cpk-configure-python
cpk-debug "<= Done!\n"

cpk-debug "=> Setting up projects..."
cpk-configure-projects
cpk-debug "<= Done!\n"

# mark this file as sourced
CPK_ENTRYPOINT_SOURCED=1
export CPK_ENTRYPOINT_SOURCED

# if anything weird happens from now on, CONTINUE
set +e

echo "<== Entrypoint"

# exit if this file is just being sourced
if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    return
fi

# reuse CPK_LAUNCHER as CMD if the var is set and the first argument is `--`
if [ ${#CPK_LAUNCHER} -gt 0 ] && [ "$1" == "--" ]; then
    shift
    exec bash -c "launcher-$CPK_LAUNCHER $*"
else
    exec "$@"
fi
