# ========================================
# Telegram Mirror Bot - Makefile
# ========================================
# Automation for common tasks
# ========================================

.PHONY: help install setup run test clean lint format check docker

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
VENV := venv
VENV_BIN := $(VENV)/bin

# Colors for output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_CYAN := \033[36m

# ========================================
# HELP
# ========================================

help: ## Show this help message
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)Telegram Mirror Bot - Available Commands$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_GREEN)%-15s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

# ========================================
# INSTALLATION
# ========================================

install: ## Install dependencies
	@echo "$(COLOR_CYAN)Installing dependencies...$(COLOR_RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(COLOR_GREEN)✅ Dependencies installed!$(COLOR_RESET)"

install-dev: ## Install development dependencies
	@echo "$(COLOR_CYAN)Installing development dependencies...$(COLOR_RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio black flake8 mypy
	@echo "$(COLOR_GREEN)✅ Development dependencies installed!$(COLOR_RESET)"

venv: ## Create virtual environment
	@echo "$(COLOR_CYAN)Creating virtual environment...$(COLOR_RESET)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(COLOR_GREEN)✅ Virtual environment created!$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Activate with: source $(VENV_BIN)/activate$(COLOR_RESET)"

# ========================================
# SETUP & RUN
# ========================================

setup: ## Run interactive setup wizard
	@echo "$(COLOR_CYAN)Running setup wizard...$(COLOR_RESET)"
	$(PYTHON) setup.py

run: ## Run the bot
	@echo "$(COLOR_CYAN)Starting Telegram Mirror Bot...$(COLOR_RESET)"
	$(PYTHON) main.py

dev: ## Run in development mode
	@echo "$(COLOR_CYAN)Starting bot in development mode...$(COLOR_RESET)"
	DEBUG=true $(PYTHON) main.py

# ========================================
# TESTING
# ========================================

test: ## Run tests
	@echo "$(COLOR_CYAN)Running tests...$(COLOR_RESET)"
	$(PYTHON) -m pytest tests/ -v

test-coverage: ## Run tests with coverage
	@echo "$(COLOR_CYAN)Running tests with coverage...$(COLOR_RESET)"
	$(PYTHON) -m pytest tests/ --cov=src --cov-report=html
	@echo "$(COLOR_GREEN)✅ Coverage report: htmlcov/index.html$(COLOR_RESET)"

# ========================================
# CODE QUALITY
# ========================================

lint: ## Run linting
	@echo "$(COLOR_CYAN)Running flake8...$(COLOR_RESET)"
	flake8 src/ --max-line-length=100 --exclude=__pycache__

format: ## Format code with black
	@echo "$(COLOR_CYAN)Formatting code with black...$(COLOR_RESET)"
	black src/ utils/ config/ --line-length=100

type-check: ## Run type checking
	@echo "$(COLOR_CYAN)Running mypy...$(COLOR_RESET)"
	mypy src/ --ignore-missing-imports

check: lint type-check ## Run all checks
	@echo "$(COLOR_GREEN)✅ All checks passed!$(COLOR_RESET)"

# ========================================
# CLEANUP
# ========================================

clean: ## Clean temporary files
	@echo "$(COLOR_CYAN)Cleaning temporary files...$(COLOR_RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf temp/* 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	@echo "$(COLOR_GREEN)✅ Cleanup complete!$(COLOR_RESET)"

clean-all: clean ## Clean everything including venv
	@echo "$(COLOR_CYAN)Removing virtual environment...$(COLOR_RESET)"
	rm -rf $(VENV)
	@echo "$(COLOR_GREEN)✅ Everything cleaned!$(COLOR_RESET)"

# ========================================
# DATABASE
# ========================================

db-backup: ## Backup MongoDB database
	@echo "$(COLOR_CYAN)Backing up database...$(COLOR_RESET)"
	mongodump --db telegram_mirror --out backups/db_$(shell date +%Y%m%d_%H%M%S)
	@echo "$(COLOR_GREEN)✅ Database backed up!$(COLOR_RESET)"

db-restore: ## Restore MongoDB database (use BACKUP=path)
	@echo "$(COLOR_CYAN)Restoring database...$(COLOR_RESET)"
	mongorestore $(BACKUP)
	@echo "$(COLOR_GREEN)✅ Database restored!$(COLOR_RESET)"

# ========================================
# DOCKER
# ========================================

docker-build: ## Build Docker image
	@echo "$(COLOR_CYAN)Building Docker image...$(COLOR_RESET)"
	docker build -t telegram-mirror:latest .
	@echo "$(COLOR_GREEN)✅ Docker image built!$(COLOR_RESET)"

docker-run: ## Run Docker container
	@echo "$(COLOR_CYAN)Running Docker container...$(COLOR_RESET)"
	docker run -d --name telegram-mirror --env-file .env telegram-mirror:latest

docker-stop: ## Stop Docker container
	@echo "$(COLOR_CYAN)Stopping Docker container...$(COLOR_RESET)"
	docker stop telegram-mirror
	docker rm telegram-mirror

# ========================================
# LOGS
# ========================================

logs: ## Show logs
	tail -f logs/bot.log

logs-error: ## Show error logs
	grep ERROR logs/bot.log | tail -n 50

# ========================================
# STATISTICS
# ========================================

stats: ## Show project statistics
	@echo "$(COLOR_CYAN)Project Statistics:$(COLOR_RESET)"
	@echo "Files: $$(find src/ -name '*.py' | wc -l)"
	@echo "Lines of code: $$(find src/ -name '*.py' -exec cat {} \; | wc -l)"
	@echo "Functions: $$(grep -r "^def " src/ | wc -l)"
	@echo "Classes: $$(grep -r "^class " src/ | wc -l)"

# ========================================
# UTILITIES
# ========================================

update: ## Update dependencies
	@echo "$(COLOR_CYAN)Updating dependencies...$(COLOR_RESET)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r requirements.txt
	@echo "$(COLOR_GREEN)✅ Dependencies updated!$(COLOR_RESET)"

freeze: ## Freeze current dependencies
	@echo "$(COLOR_CYAN)Freezing dependencies...$(COLOR_RESET)"
	$(PIP) freeze > requirements.lock
	@echo "$(COLOR_GREEN)✅ Dependencies frozen to requirements.lock!$(COLOR_RESET)"

info: ## Show environment info
	@echo "$(COLOR_CYAN)Environment Information:$(COLOR_RESET)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "Virtual Env: $$(if [ -d $(VENV) ]; then echo 'Active'; else echo 'Not created'; fi)"
	@echo "Config: $$(if [ -f .env ]; then echo 'Found'; else echo 'Not found'; fi)"
