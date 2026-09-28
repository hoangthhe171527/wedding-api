# Máy dev KHÔNG cài Python — mọi lệnh chạy trong container.
# Dùng: make up, make seed, make test, make lint

SHELL := /bin/bash
COMPOSE := docker compose
API := $(COMPOSE) exec -T api

.DEFAULT_GOAL := help
.PHONY: help up down restart build logs ps seed test test-one lint format lock shell mongo reset

help: ## Danh sách lệnh
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Dựng toàn bộ hạ tầng (mongodb, redis, api)
	$(COMPOSE) up -d --build
	@echo "API: http://localhost:28080/docs"

down: ## Dừng và xoá container (giữ dữ liệu)
	$(COMPOSE) down

reset: ## Xoá sạch cả volume — MẤT TOÀN BỘ DỮ LIỆU LOCAL
	$(COMPOSE) down -v

restart: ## Khởi động lại api
	$(COMPOSE) restart api

build: ## Build lại image
	$(COMPOSE) build

ps: ## Trạng thái các service
	$(COMPOSE) ps

logs: ## Theo dõi log api
	$(COMPOSE) logs -f api

seed: ## Nạp dữ liệu mẫu (idempotent)
	$(API) python -m app.seeds.seed

test: ## Chạy pytest
	$(API) pytest

test-one: ## Chạy một test: make test-one t=tests/modules/identity/test_auth.py
	$(API) pytest $(t) -vv

lint: ## ruff check + ruff format --check + mypy
	$(API) ruff check app tests
	$(API) ruff format --check app tests
	$(API) mypy

format: ## ruff format + tự sửa lint
	$(API) ruff format app tests
	$(API) ruff check --fix app tests

lock: ## Sinh lại uv.lock trong container (máy dev không có uv)
	docker run --rm -v "$(CURDIR):/work" -w /work ghcr.io/astral-sh/uv:0.5-python3.12-bookworm-slim uv lock

shell: ## Mở shell trong container api
	$(COMPOSE) exec api bash

mongo: ## Mở mongosh
	$(COMPOSE) exec mongodb mongosh wedding
