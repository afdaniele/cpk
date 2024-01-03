#!/bin/bash

# NOTE: do not use variables in this file path, they are not loaded yet
source "/cpk/constants.sh"

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


cpk-configure-environment.d() {
    # source all the environment.d scripts provided by the projects
    for candidate_project in ${ALL_PROJECTS}; do
        project_dir="$(realpath $(dirname "${candidate_project}")/../)"
        candidate_environmentd_dir="${project_dir}/assets/environment.d"
        if [ -d "${candidate_environmentd_dir}" ]; then
            cpk-debug "   > Entering ${candidate_environmentd_dir}/"
            for f in $(find "${candidate_environmentd_dir}" -mindepth 1 -maxdepth 1 -type f -name "*.sh" | sort); do
                cpk-debug "     > Sourcing ${f}"
                source ${f}
                cpk-debug "     < Sourced  ${f}"
            done
            cpk-debug "   < Exiting ${candidate_environmentd_dir}/"
        fi
    done
}

if [ "${CPK_ENVIRONMENT_SOURCED:-0}" != "1" ]; then
    cpk-debug "=> Environment"

    cpk-debug " > Setting up PYTHONPATH..."
    cpk-configure-python
    cpk-debug " < Done!"

    cpk-debug " > Setting up libraries..."
    cpk-configure-libraries
    cpk-debug " < Done!"

    cpk-debug " > Setting up environment..."
    cpk-configure-environment.d
    cpk-debug " < Done!"

    # mark this file as sourced
    CPK_ENVIRONMENT_SOURCED=1
    export CPK_ENVIRONMENT_SOURCED

    cpk-debug "<= Environment"
fi


# if anything weird happens from now on, CONTINUE
set +e
