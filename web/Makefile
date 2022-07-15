DOCKER_REPO=docker.dev.formlabs.cloud
APP_NAME=hackathon/novacancy-web
VERSION=latest
TAG=$(DOCKER_REPO)/$(APP_NAME):$(VERSION)


# Build the container
build:
	docker build .. -f Dockerfile -t $(TAG)

run:
	make build && docker run --env-file=../.env -p 5000:5000 $(TAG)

push:
	make build && docker push $(TAG)

deploy:
	make push && kubectl apply -f k8s/borg.yaml
	kubectl scale deployment novacancy --replicas=0 -n mfg
	kubectl scale deployment novacancy --replicas=1 -n mfg
