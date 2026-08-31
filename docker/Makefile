# Zion-HQ — Docker build/run helpers.
#
# Targets:
#   build           build the api+gateway runtime image
#   build-web       build the web frontend image
#   up              bring up the full stack (compose)
#   down            tear down the stack
#   logs            tail stack logs
#   ps              show stack status
#   clean           remove built images
#
# Stateful deps (postgres/redis/minio/keycloak) come from infra/docker-compose.yml
# during local dev; docker-compose.yml in this dir is the full production stack.

IMAGE      ?= zionhq
TAG        ?= latest

# Resolve this docker/ directory and the repo root from the Makefile's own
# location, so the targets work no matter where make is invoked from (make -C
# docker from the repo root, or make -f docker/Makefile from an IDE).
DOCKER_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
HQ_ROOT    := $(patsubst %/,%,$(dir $(DOCKER_DIR)))
COMPOSE    := docker compose -f $(DOCKER_DIR)/docker-compose.yml --env-file $(HQ_ROOT)/.env

.PHONY: build build-web up down logs ps clean

build: ## Build the API + agent-gateway runtime image
	docker build -f $(DOCKER_DIR)/Dockerfile -t $(IMAGE)-backend:$(TAG) $(HQ_ROOT)

build-web: ## Build the web frontend image
	docker build -f $(DOCKER_DIR)/Dockerfile.web -t $(IMAGE)-web:$(TAG) $(HQ_ROOT)

up: ## Bring up the full stack
	$(COMPOSE) up -d --build

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Tail stack logs
	$(COMPOSE) logs -f

ps: ## Show stack status
	$(COMPOSE) ps

clean: ## Remove built images
	docker rmi $(IMAGE)-backend:$(TAG) $(IMAGE)-web:$(TAG) 2>/dev/null || true
