build:
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a amd64 \
		amd64/ubuntu:bionic \
		cpkbase/ubuntu:bionic
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm32v7 \
		arm32v7/ubuntu:bionic \
		cpkbase/ubuntu:bionic
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm64v8 \
		arm64v8/ubuntu:bionic \
		cpkbase/ubuntu:bionic

push:
	docker push \
		cpkbase/ubuntu:bionic-amd64
	docker push \
		cpkbase/ubuntu:bionic-arm32v7
	docker push \
		cpkbase/ubuntu:bionic-arm64v8

release: build push
