# Colors
GREEN	:=	\033[0;32m
CYAN	:= 	\033[0;36m
RED 	:=	\033[0;31m
END		:=	\033[0m

.PHONY: help
help: # Show help for each of the Makefile recipes.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

.PHONY: new-migration
new-migration: # Create a new migration file. Usage: make new-migration name=<name>
	@goose -dir db/migrations create $(name) sql

.PHONY: migrate-up
migrate-up: # Run database migrations
	go run scripts/migrate/migrate.go -up

.PHONY: migrate-down
migrate-down: # Rollback to to previous migration
	go run scripts/migrate/migrate.go -down

