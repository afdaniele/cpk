# parameters
ARG ARCH

ARG BASE_REGISTRY
ARG BASE_ORGANIZATION
ARG BASE_REPOSITORY
ARG BASE_TAG

ARG CPK_VERSION="NOT_SET"

# ---
# base image
FROM ${BASE_REGISTRY}/${BASE_ORGANIZATION}/${BASE_REPOSITORY}:${BASE_TAG}

# recall all arguments
ARG ARCH

ARG BASE_REGISTRY
ARG BASE_ORGANIZATION
ARG BASE_REPOSITORY
ARG BASE_TAG

ARG CPK_VERSION
ARG LAUNCHER=bash

# copy QEMU
COPY ./assets/qemu/${ARCH}/ /usr/bin/

# setup environment
ENV INITSYSTEM="off" \
    QEMU_EXECVE="1" \
    TERM="xterm" \
    LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONIOENCODING="UTF-8" \
    DEBIAN_FRONTEND="noninteractive" \
    # cpk environment
    CPK_VERSION="${CPK_VERSION}" \
    CPK_CODE_DIR="/code" \
    CPK_SOURCE_DIR="/code/src" \
    CPK_INSTALL_DIR="/cpk" \
    CPK_DECORATOR_DIR="/cpk/decorator" \
    CPK_LAUNCHER="${LAUNCHER}" \
    # CPK user
    CPK_USER_NAME="cpk" \
    CPK_USER_UID=2222 \
    CPK_GROUP_NAME="cpk" \
    CPK_GROUP_GID=2222 \
    CPK_USER_HOME="/home/cpk"

# copy everything
COPY . ${CPK_DECORATOR_DIR}/

# decorate
RUN ${CPK_DECORATOR_DIR}/assets/bin/cpk-decorate

# define healthcheck
HEALTHCHECK \
    --interval=10s \
    CMD cat /health && grep -q ^healthy$ /health

# define entrypoint
ENTRYPOINT ["tini", "--", "/cpk/entrypoint.sh", "--"]
