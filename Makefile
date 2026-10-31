AWS_REGION ?= us-east-1
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_REGION PROJECT_NAME
export MSYS_NO_PATHCONV := 1
export MSYS2_ARG_CONV_EXCL := *

AWS ?= docker run --rm \
    -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
    -e AWS_DEFAULT_REGION=$(AWS_REGION) \
    -v $(CURDIR):/aws -w /aws \
    amazon/aws-cli:latest

IMAGE_TAG ?= latest
AWS_LAMBDA_ARCH ?= x86_64
IMAGE_PLATFORM = $(if $(filter arm64,$(AWS_LAMBDA_ARCH)),linux/arm64,linux/amd64)

require-aws-credentials = @test -n "$(AWS_ACCESS_KEY_ID)" -a -n "$(AWS_SECRET_ACCESS_KEY)" || { echo "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are empty — set them in .env"; exit 1; }
require-db-password = @test -n "$(AWS_DB_PASSWORD)" || { echo "AWS_DB_PASSWORD is empty — set it in .env (8+ chars, [A-Za-z0-9_-] only)"; exit 1; }

.PHONY: help up up-build down down-v logs ps migrate revision seed test lint fmt shell-backend psql \
    infra-init infra-plan infra-output report-now llm-hello parse

help: ## Show this help message
	@grep -hE '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1,$$2}'

up: ## Start the whole stack
	$(COMPOSE) up

up-build: ## Rebuild images and start the whole stack
	$(COMPOSE) up --build

down: ## Stop the stack
	$(COMPOSE) down

down-v: ## Stop the stack and delete the database volume
	$(COMPOSE) down -v

logs: ## Follow logs from every service
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

migrate: ## Apply database migrations
	$(COMPOSE) exec backend alembic upgrade head

revision: ## Autogenerate a migration: make revision m="add column"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

seed: ## Insert demo meetings for today for one user: make seed owner=<cognito-sub>
	@test -n "$(owner)" || { echo "Usage: make seed owner=<cognito-sub> (the user's sub from the Cognito console)"; exit 1; }
	$(COMPOSE) exec backend python -m app.seed "$(owner)"

test: ## Run the backend test suite against a throwaway database
	$(COMPOSE) exec db psql -U app -d postgres -tc \
		"SELECT 1 FROM pg_database WHERE datname='meetings_test'" | grep -q 1 || \
		$(COMPOSE) exec db createdb -U app meetings_test
	$(COMPOSE) exec -e DATABASE_URL=postgresql+asyncpg://app:app@db:5432/meetings_test backend pytest -q

lint: ## Lint backend and frontend
	$(COMPOSE) exec backend ruff check
	$(COMPOSE) exec frontend npm run lint

fmt: ## Format the backend code
	$(COMPOSE) exec backend ruff format .

shell-backend: ## Open a shell in the backend container
	$(COMPOSE) exec backend sh

psql: ## Open psql against the application database
	$(COMPOSE) exec db psql -U app -d meetings

# --- Terraform Infrastructure Targets ---

infra-init: ## Initialize Terraform in infra directory
	cd infra && terraform init

infra-plan: ## Run Terraform plan in infra directory
	cd infra && terraform plan

infra-output: ## Get the deployed Lambda Agenda Parser Function URL from Terraform outputs
	cd infra && terraform output -raw agenda_parser_function_url

# --- Utility & Helper Targets ---

report-now: ## Send an on-demand report request: make report-now WEEK=2026-W39
	$(require-aws-credentials)
	@test -n "$(WEEK)" || { echo "Usage: make report-now WEEK=2026-W39"; exit 1; }
	@queue_url=$$(cd infra && terraform output -raw report_requests_queue_url 2>/dev/null | tr -d '[:space:]'); \
		echo "Sending report request for $(WEEK) to $$queue_url"; \
		$(AWS) sqs send-message --queue-url "$$queue_url" --message-body '{"week": "$(WEEK)", "source": "sqs"}'

llm-hello: ## Run a simple Bedrock LLM call to verify access and credentials
	python scripts/llm_hello.py

parse: ## Run test agenda parse script
	python scripts/test_parse.py
