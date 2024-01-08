ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PART=patch
PROJECT_NAME=cpk
TEST=*

all:

new-dist:
	$(MAKE) clean bump-upload

bump-upload:
	$(MAKE) test bump upload

bump:
	bumpversion ${PART}

upload:
	git push --tags
	git push
	$(MAKE) clean
	$(MAKE) build
	twine upload dist/*

build:
	python3 setup.py sdist

install:
	python3 setup.py install --record files.txt

clean:
	rm -rf dist/ build/ ${PROJECT_NAME}.egg-info/ MANIFEST

uninstall:
	xargs rm -rf < files.txt

format:
	yapf -r -i -p -vv ${ROOT_DIR}

build-image-ubuntu-jammy:
	$(MAKE) -f ${ROOT_DIR}/images/ubuntu/jammy/Makefile build

new-dist-image-ubuntu-jammy:
	$(MAKE) -f ${ROOT_DIR}/images/ubuntu/jammy/Makefile build

test:
	$(MAKE) test-unit
	$(MAKE) test-distribution

test-unit:
	@echo "Running unit tests:"; echo ""
	@PYTHONPATH="${ROOT_DIR}/include/:$${PYTHONPATH}" \
		python3 \
			-m unittest discover \
			--verbose \
			-s "${ROOT_DIR}/tests/unit" \
			-p "test_*.py" \
			-k "${TEST}"

test-internal:
	@echo "Running internal units tests:"; echo ""
	@PYTHONPATH="${ROOT_DIR}/include/:$${PYTHONPATH}" \
		python3 \
			-m unittest discover \
			--verbose \
			-s "${ROOT_DIR}/tests/unit" \
			-p "test_internal_*.py"

test-build:
	$(MAKE) -f ${ROOT_DIR}/tests/build/Makefile test

test-distribution:
	$(MAKE) -f ${ROOT_DIR}/tests/distribution/Makefile test-all

test-distribution-3.6:
	$(MAKE) -f ${ROOT_DIR}/tests/distribution/Makefile test-no-clean PYTHON_VERSION=3.6;

