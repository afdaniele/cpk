#!/bin/bash

source "/cpk/constants.sh"

# get container ID
CPK_CONTAINER_ID=$(basename "$(cat /proc/1/cpuset)")
export CPK_CONTAINER_ID
