MAKEFILE_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

models:
	datamodel-codegen --input ${MAKEFILE_DIR}/compose-spec.json --input-file-type jsonschema --output ${MAKEFILE_DIR}/../../models/docker/compose.py --output-model-type dataclasses.dataclass
