MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

build_all:
	for project in level1 level2 level3 level4 ; do \
		${MAKEFILE_DIR}/../../tests/cpk build -C ${MAKEFILE_DIR}/$${project} > /dev/null; \
	done
