#!/bin/bash

# make sure the user environment is loaded for both interactive and non-interactive shells
echo "source ${CPK_INSTALL_DIR}/environment.sh" >> /etc/bash.bashrc
export BASH_ENV="${CPK_INSTALL_DIR}/environment.sh"
