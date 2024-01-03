# parameters
ARG ARCH
ARG BASE_REGISTRY
ARG BASE_ORGANIZATION
ARG BASE_REPOSITORY
ARG BASE_TAG

# ==================================================>
# ==> Do not change the code below this line

# define base image
FROM ${BASE_REGISTRY}/${BASE_ORGANIZATION}/${BASE_REPOSITORY}:${BASE_TAG}-${ARCH} as BASE

# recall all arguments
# - base project
ARG BASE_REGISTRY
ARG BASE_ORGANIZATION
ARG BASE_REPOSITORY
ARG BASE_TAG
# - defaults
ARG LAUNCHER=default
# - current project
ARG PROJECT_NAME

# define/create project paths
ARG PROJECT_PATH="${CPK_SOURCE_DIR}/${PROJECT_NAME}"
WORKDIR "${PROJECT_PATH}"

# keep some arguments as environment variables
ENV CPK_PROJECT_NAME="${PROJECT_NAME}" \
    CPK_PROJECT_PATH="${PROJECT_PATH}" \
    CPK_LAUNCHER="${LAUNCHER}"

# install apt dependencies
COPY ./dependencies-apt.txt "${PROJECT_PATH}/"
RUN cpk-apt-install ${PROJECT_PATH}/dependencies-apt.txt

# install python3 dependencies
COPY ./dependencies-py3.txt "${PROJECT_PATH}/"
RUN cpk-pip3-install ${PROJECT_PATH}/dependencies-py3.txt

# install project code
COPY . "${PROJECT_PATH}/"

# store project metadata
LABEL cpk.label.project.${ORGANIZATION}.${PROJECT_NAME}.code.location="${PROJECT_PATH}"
# <== Do not change the code above this line
# <==================================================

# install pytorch
ARG ARCH
RUN if [ "${ARCH}" = "amd64" ]; then \
        pip3 install https://download.pytorch.org/whl/cu113/torch-1.12.0%2Bcu113-cp38-cp38-linux_x86_64.whl; \
    fi; \
    if [ "${ARCH}" = "arm64v8" ]; then \
        pip3 install https://download.pytorch.org/whl/cpu/torch-1.12.0-cp38-cp38-manylinux2014_aarch64.whl; \
    fi;