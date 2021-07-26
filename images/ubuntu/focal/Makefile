build:
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a amd64 \
		amd64/ubuntu:focal \
		cpkbase/ubuntu:focal
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm32v7 \
		arm32v7/ubuntu:focal \
		cpkbase/ubuntu:focal
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm64v8 \
		arm64v8/ubuntu:focal \
		cpkbase/ubuntu:focal

push:
	docker push \
		cpkbase/ubuntu:focal-amd64
	docker push \
		cpkbase/ubuntu:focal-arm32v7
	docker push \
		cpkbase/ubuntu:focal-arm64v8

release: build push
