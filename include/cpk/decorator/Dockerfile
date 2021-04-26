# parameters
ARG ARCH
ARG MAINTAINER

ARG BASE_REGISTRY="NOT_SET"
ARG BASE_ORGANIZATION="NOT_SET"
ARG BASE_REPOSITORY="NOT_SET"
ARG BASE_TAG="NOT_SET"

ARG ORGANIZATION="NOT_SET"
ARG NAME="NOT_SET"

ARG CPK_VERSION="NOT_SET"

# ---
# base image
FROM ${BASE_REGISTRY}/${BASE_ORGANIZATION}/${BASE_REPOSITORY}:${BASE_TAG}

# recall all arguments
ARG ARCH
ARG MAINTAINER

ARG BASE_REGISTRY
ARG BASE_ORGANIZATION
ARG BASE_REPOSITORY
ARG BASE_TAG

ARG ORGANIZATION
ARG NAME

ARG CPK_VERSION

ARG LAUNCHER=default

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
    CPK_SOURCE_DIR="/code" \
    CPK_LAUNCHERS_DIR="/launchers" \
    CPK_INSTALL_DIR="/cpk"

# define/create project paths
ARG PROJECT_PATH="${CPK_SOURCE_DIR}/cpk"
ARG PROJECT_LAUNCHERS_PATH="${CPK_LAUNCHERS_DIR}/cpk"
RUN mkdir -p ${CPK_INSTALL_DIR}/bin && \
    mkdir -p "${PROJECT_PATH}" && \
    mkdir -p "${PROJECT_LAUNCHERS_PATH}"
WORKDIR "${PROJECT_PATH}"

# copy binaries
COPY ./assets/bin/. ${CPK_INSTALL_DIR}/bin/
ENV PATH="${PATH}:${CPK_INSTALL_DIR}/bin"

# copy entrypoint and environment
COPY ./assets/entrypoint.sh ${CPK_INSTALL_DIR}/entrypoint.sh
COPY ./assets/environment.sh ${CPK_INSTALL_DIR}/environment.sh

# keep some arguments as environment variables
ENV \
    CPK_BASE_NAME="${NAME}" \
    CPK_BASE_ORGANIZATION="${ORGANIZATION}" \
    CPK_BASE_DESCRIPTION="cpk base image" \
    CPK_BASE_MAINTAINER="${MAINTAINER}" \
    CPK_BASE_PATH="${PROJECT_PATH}" \
    CPK_BASE_LAUNCHERS_PATH="${PROJECT_LAUNCHERS_PATH}" \
    CPK_LAUNCHER="${LAUNCHER}"

# install dependencies (APT)
COPY ./dependencies-apt.txt "${PROJECT_PATH}/"
RUN cpk-apt-install "${PROJECT_PATH}/dependencies-apt.txt"

# install dependencies (PIP3)
COPY ./dependencies-py3.txt "${PROJECT_PATH}/"
RUN cpk-pip3-install "${PROJECT_PATH}/dependencies-py3.txt"

# define healthcheck
RUN echo ND > /health
RUN chmod 777 /health
HEALTHCHECK \
    --interval=5s \
    CMD cat /health && grep -q ^healthy$ /health

# copy the source code
COPY ./packages "${PROJECT_PATH}/packages"

# install launcher scripts
COPY ./launchers/. "${PROJECT_LAUNCHERS_PATH}/"
COPY ./launchers/default.sh "${PROJECT_LAUNCHERS_PATH}/"
RUN cpk-install-launchers "${PROJECT_LAUNCHERS_PATH}"

# copy setup file
COPY ./setup.sh ${PROJECT_PATH}/

# source environment on every bash session
RUN echo "source ${CPK_INSTALL_DIR}/environment.sh" >> ~/.bashrc

# configure entrypoint
ENTRYPOINT ["/cpk/entrypoint.sh"]

# define default command
CMD ["bash", "-c", "launcher-${CPK_LAUNCHER}"]

# store module metadata
LABEL \
    cpk.label.current="${ORGANIZATION}.${NAME}" \
    cpk.label.base="${ORGANIZATION}.${NAME}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.description="${CPK_BASE_DESCRIPTION}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.code.location="${PROJECT_PATH}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.base.registry="${BASE_REGISTRY}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.base.organization="${BASE_ORGANIZATION}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.base.project="${BASE_REPOSITORY}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.base.tag="${BASE_TAG}" \
    cpk.label.project.${ORGANIZATION}.${NAME}.maintainer="${MAINTAINER}" \
    cpk.label.cpk.version="${CPK_VERSION}" \
    cpk.label.architecture="${ARCH}"
