ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

test:
	@echo "Running build tests:"; echo ""
	PYTHONPATH="${ROOT_DIR}/../../include/:$${PYTHONPATH}" \
		python3 \
			-m unittest discover \
			--verbose \
			-s "${ROOT_DIR}" \
			-p "test_*.py"
