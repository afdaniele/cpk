#!/bin/bash

# reset health
(echo ND | tee /health) || :

# get container ID
CPK_CONTAINER_ID=$(basename "$(cat /proc/1/cpuset)")
export CPK_CONTAINER_ID
