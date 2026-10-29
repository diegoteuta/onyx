# =============================================================================
# Onyx - automatizacion de tareas
# =============================================================================

ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
SHELL := /bin/bash
PYTHON ?= python3
endif

.DEFAULT_GOAL := help
.PHONY: help install dev pre-commit-install pre-commit lint format format-check typecheck test check build clean discover ingest report

help: ## Muestra esta ayuda
	@$(PYTHON) -c "import re; [print(f'  {m.group(1):<18} {m.group(2)}') for m in (re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', l) for l in open('Makefile', encoding='utf-8')) if m]"

install: ## Sincroniza el entorno virtual e instala dependencias
	uv sync

dev: install pre-commit-install ## Prepara el entorno de desarrollo (sync + hooks)

pre-commit-install: ## Instala los hooks de pre-commit en el repositorio local
	uv run pre-commit install

pre-commit: ## Ejecuta todos los hooks de pre-commit sobre el repositorio
	uv run pre-commit run --all-files

lint: ## Ejecuta Ruff (lint)
	uv run ruff check .

format: ## Formatea el codigo con Ruff
	uv run ruff format .

format-check: ## Verifica el formato sin modificarlo
	uv run ruff format --check .

typecheck: ## Verifica los tipos con ty (Astral)
	uv run ty check

test: ## Ejecuta las pruebas
	uv run pytest

check: lint format-check typecheck test ## Verificacion completa (lint + formato + tipos + pruebas)

discover: ## Lista las URLs que Onyx encontraria para SITE (ej: make discover SITE=hv)
	uv run onyx discover --site $(SITE)

ingest: ## Ejecuta el pipeline completo Bronze -> Silver -> Gold para SITE
	uv run onyx ingest --site $(SITE)

report: ## Muestra el estado del corpus de SITE
	uv run onyx report --site $(SITE)

build: ## Construye el paquete (sdist + wheel)
	uv build

clean: ## Limpia caches y artefactos
	@$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache','.ruff_cache','.mypy_cache','dist','build','htmlcov']]"
	@$(PYTHON) -c "import pathlib, shutil; [shutil.rmtree(d, ignore_errors=True) for d in pathlib.Path('.').rglob('__pycache__')]"
