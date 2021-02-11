# parameters
ARG NAME
ARG DESCRIPTION
ARG MAINTAINER
ARG ARCH

# ==================================================>
# ==> Do not change the code below this line
ARG LAUNCHER=default

# define base image
FROM cpk/ubuntu:focal-${ARCH} as BASE

# recall all arguments
ARG ARCH
ARG NAME
ARG DESCRIPTION
ARG MAINTAINER
ARG LAUNCHER

# define/create project paths
ARG PROJECT_PATH="${CPK_SOURCE_DIR}/${NAME}"
ARG PROJECT_LAUNCHERS_PATH="${CPK_LAUNCHERS_DIR}/${NAME}"
RUN mkdir -p "${PROJECT_PATH}"
RUN mkdir -p "${PROJECT_LAUNCHERS_PATH}"
WORKDIR "${PROJECT_PATH}"

# keep some arguments as environment variables
ENV \
    CPK_PROJECT_NAME="${NAME}" \
    CPK_PROJECT_DESCRIPTION="${DESCRIPTION}" \
    CPK_PROJECT_MAINTAINER="${MAINTAINER}" \
    CPK_PROJECT_PATH="${PROJECT_PATH}" \
    CPK_PROJECT_LAUNCHERS_PATH="${PROJECT_LAUNCHERS_PATH}" \
    CPK_LAUNCHER="${LAUNCHER}"

# copy the source code
COPY ./packages "${CPK_PROJECT_PATH}/packages"


# install launcher scripts
COPY ./launchers/. "${PROJECT_LAUNCHERS_PATH}/"
COPY ./launchers/default.sh "${PROJECT_LAUNCHERS_PATH}/"
RUN cpk-install-launchers "${PROJECT_LAUNCHERS_PATH}"

# define default command
CMD ["bash", "-c", "cpk-launcher-${CPK_LAUNCHER}"]

# store module metadata
#LABEL \
#    cpk.label.project.name="${NAME}" \
#    cpk.label.project.description="${DESCRIPTION}" \
#    cpk.label.architecture="${ARCH}" \
#    cpk.label.code.location="${PROJECT_PATH}" \
#    cpk.label.code.version.distro="${DISTRO}" \
#    cpk.label.base.image="${BASE_IMAGE}" \
#    cpk.label.base.tag="${BASE_TAG}" \
#    cpk.label.maintainer="${MAINTAINER}"
# <== Do not change the code above this line
# <==================================================
