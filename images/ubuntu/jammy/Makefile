build:
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a amd64 \
		amd64/ubuntu:jammy \
		cpkbase/ubuntu:jammy
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm32v7 \
		arm32v7/ubuntu:jammy \
		cpkbase/ubuntu:jammy
	cpk decorate \
		-m "Andrea F. Daniele" \
		-e "afdaniele@ttic.edu" \
		-a arm64v8 \
		arm64v8/ubuntu:jammy \
		cpkbase/ubuntu:jammy

push:
	docker push \
		cpkbase/ubuntu:jammy-amd64
	docker push \
		cpkbase/ubuntu:jammy-arm32v7
	docker push \
		cpkbase/ubuntu:jammy-arm64v8

release: build push
