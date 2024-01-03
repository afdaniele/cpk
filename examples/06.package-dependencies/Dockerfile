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

# install project code
COPY . "${PROJECT_PATH}/"

# install packages dependencies
RUN cpk-install-packages-dependencies

# store project metadata
LABEL cpk.label.project.${ORGANIZATION}.${PROJECT_NAME}.code.location="${PROJECT_PATH}"
# <== Do not change the code above this line
# <==================================================
