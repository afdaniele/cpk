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
ARG LAUNCHER=bash
# - current project
ARG PROJECT_NAME

# define/create project paths
ARG PROJECT_PATH="${CPK_SOURCE_DIR}/${PROJECT_NAME}"
ARG PROJECT_LAUNCHERS_PATH="${CPK_LAUNCHERS_DIR}/${PROJECT_NAME}"
RUN mkdir -p "${PROJECT_PATH}" "${PROJECT_LAUNCHERS_PATH}"
WORKDIR "${PROJECT_PATH}"

# keep some arguments as environment variables
ENV CPK_PROJECT_NAME="${PROJECT_NAME}" \
    CPK_PROJECT_PATH="${PROJECT_PATH}" \
    CPK_PROJECT_LAUNCHERS_PATH="${PROJECT_LAUNCHERS_PATH}" \
    CPK_LAUNCHER="${LAUNCHER}"

# define default command
CMD ["bash", "-c", "launcher-${CPK_LAUNCHER}"]

# store project metadata
LABEL cpk.label.project.${ORGANIZATION}.${PROJECT_NAME}.code.location="${PROJECT_PATH}"
# <== Do not change the code above this line
# <==================================================
