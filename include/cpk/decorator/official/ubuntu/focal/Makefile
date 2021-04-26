# TODO: this is deprecated, use `cpk decorate` instead

#MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
#ROOT_DIR:=${MAKEFILE_DIR}/../../..
#
#IN_REGISTRY=docker.io
#IN_IMAGE=ubuntu
#IN_TAG=focal
#
#MAINTAINER="Andrea F. Daniele (afdaniele@ttic.edu)"
#
#OUT_REGISTRY=docker.io
#OUT_REPOSITORY=cpkbase
#OUT_IMAGE=ubuntu
#OUT_TAG=focal
#
## TODO: get this from git tag and make sure the index is clean
#CPK_VERSION="NOT_SET"
#
#all:
#
#	#for arch in amd64 ; do \
#
#	for arch in amd64 arm32v7 arm64v8 ; do \
#		docker build \
#			-t "${OUT_REGISTRY}/${OUT_REPOSITORY}/${OUT_IMAGE}:${OUT_TAG}-$${arch}" \
#			-f ${ROOT_DIR}/Dockerfile \
#			--build-arg ARCH="$${arch}" \
#			--build-arg BASE_REGISTRY="${IN_REGISTRY}" \
#			--build-arg BASE_REPOSITORY="$${arch}" \
#			--build-arg BASE_IMAGE="${IN_IMAGE}" \
#			--build-arg BASE_TAG="${IN_TAG}" \
#			--build-arg ORGANIZATION="${OUT_REPOSITORY}" \
#			--build-arg NAME="${OUT_IMAGE}" \
#			--build-arg MAINTAINER=${MAINTAINER} \
#			--build-arg CPK_VERSION="${CPK_VERSION}" \
#			${ROOT_DIR}; \
#    done;
