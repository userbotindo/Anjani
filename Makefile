VERSION	:=	$(shell grep -m 1 version pyproject.toml | cut -d '"' -f 2)

CHANGELOG_FILE := CHANGELOG.md

# Colors
GREEN	:=	\033[0;32m
CYAN	:= 	\033[0;36m
RED 	:=	\033[0;31m
END		:=	\033[0m

.PHONY: help pull build start down restart logs status up changelog bump

all: pull build stop start

help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

pull: # Pull latest changes from git
	@echo "> $(GREEN)Pulling latest changes from git$(END)"
	@git pull origin

build: # Build docker images
	@echo "> $(CYAN)Building images$(END)"
	@docker compose build

start: # Start docker containers
	@echo "> $(CYAN)Creating containers$(END)"
	@docker compose create
	@echo "> $(CYAN)Starting containers$(END)"
	@docker compose start

stop: # Stop docker containers
	@echo "> $(CYAN)Stopping containers$(END)"
	@docker compose stop

down: # Stop and remove docker containers
	@echo "> $(CYAN)Stopping and removing containers$(END)"
	@docker compose down

restart: # Restart docker containers
	@echo "> $(CYAN)Restarting containers$(END)"
	@docker compose restart

logs: # View docker logs
	@docker compose logs -f

status: # View docker status
	@docker compose ps

up: all  # Pull latest changes, build docker images, stop and start docker containers

.ONESHELL:
changelog: # Generate changelog https://convco.github.io/
	@echo "$(GREEN)Generating changelog$(END)"
	@convco changelog -m 1 > $(CHANGELOG_FILE)
	@echo "\n### Version Contributor(s)\n" >> $(CHANGELOG_FILE)
	@echo $(shell git log --pretty=oneline HEAD...v$(VERSION) --format="@%cN" | sort | uniq | sed s/"@GitHub"// | tr '\n' ' ') >> $(CHANGELOG_FILE)
	@echo "$(GREEN)Changelog saved to $(CHANGELOG_FILE)$(END)"

.ONESHELL:
_bump:
	@echo "$(GREEN)Updating version$(END)"
	@echo "$(GREEN)Current version: v$(VERSION)$(END)"
	NEW_VERSION=$(shell convco version --bump)
	@echo "$(GREEN)Bumping version to v$$NEW_VERSION$(END)"

	@sed -i "s/version = \"$(VERSION)\"/version = \"$$NEW_VERSION\"/g" pyproject.toml > /dev/null;
	@sed -i "s/__version__ = \"$(VERSION)\"/__version__ = \"$$NEW_VERSION\"/g" anjani/__init__.py > /dev/null;
	@git add pyproject.toml anjani/__init__.py > /dev/null

	@echo "$(GREEN)Commiting changes$(END)"
	@git commit -m "Bump version to v$$NEW_VERSION"
	@git tag -a "v$$NEW_VERSION" -m "Bump version to v$$NEW_VERSION"
	@git checkout master
	@git push --atomic origin master "v$$NEW_VERSION"

bump: _bump changelog # Bump version, generate changelog and push to git
