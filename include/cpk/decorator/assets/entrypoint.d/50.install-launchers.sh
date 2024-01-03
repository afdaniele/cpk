#!/usr/bin/env bash

ALL_PROJECTS=$(find "${CPK_SOURCE_DIR}/" -path \*/cpk/self.yaml -type f -printf "%T@ %p\n" | sort -n -r | awk '{print $2}')

cpk-debug "       > Setting up launchers..."

# install all launchers provided by the projects
for candidate_project in ${ALL_PROJECTS}; do
    project_dir="$(realpath $(dirname "${candidate_project}")/../)"
    candidate_launchers_dir="${project_dir}/launchers"
    if [ -d "${candidate_launchers_dir}" ]; then
        cpk-debug "         > Entering ${candidate_launchers_dir}/"
        BASH_ENV= cpk-install-launchers "${candidate_launchers_dir}"
        cpk-debug "         < Exiting ${candidate_launchers_dir}/"
    fi
done

cpk-debug "       < Done!"
