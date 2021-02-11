MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

build_all:
	for project in basic dependencies git packages ; do \
		${MAKEFILE_DIR}/../tests/cpk build -C ${MAKEFILE_DIR}/$${project} > /dev/null; \
	done
