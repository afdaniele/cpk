MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

models:
	datamodel-codegen --input ${MAKEFILE_DIR}/compose-spec.json --output ${MAKEFILE_DIR}/../../models/docker/compose.py
