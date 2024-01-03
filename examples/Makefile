MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

build_all:
	for project in $(shell find ${MAKEFILE_DIR} -path "*/cpk/self.yaml" -exec dirname {} \; | sort); do \
		${MAKEFILE_DIR}/../tests/cpk build -C $${project}/../ > /dev/null; \
	done
