DOCKER_REPO=docker.dev.formlabs.cloud
APP_NAME=hackathon/novacancy
VERSION=latest
TAG=$(DOCKER_REPO)/$(APP_NAME):$(VERSION)

# Build the container
build:
	docker build -t $(TAG) .

sheets_example:
	make build && docker run  --env-file=.env $(TAG) python3 sheets_example.py

