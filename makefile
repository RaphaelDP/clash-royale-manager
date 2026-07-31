# =========================================
# Project: clash-royale-manager
# Purpose: Formatting & linting utilities
# =========================================

.PHONY: install format lint check format-check lint-ci ci run tree commit clean reset-db

# Python executable (assumes venv is activated)
PYTHON := python

# Tools (resolved from active environment)
BLACK := black
PYLINT := pylint

# Project paths
SRC := dashboard app scripts tests

# Files and directories to ignore
IGNORE := venv,.venv,logs,data,secrets,app/database/migrations/

# Convert ignore list to pylint format (comma separated)
PYLINT_IGNORE := $(subst $(space),,$(IGNORE))


#
# Installation
#
install:
	pip install -r requirements.txt

# -----------------------------------------
# Formatting
# -----------------------------------------
format:
	@echo "Running Black formatter..."
	$(BLACK) $(SRC)

# -----------------------------------------
# Linting
# -----------------------------------------
lint:
	@echo "Running Pylint..."
	$(PYLINT) --rcfile=.pylintrc \
		--recursive=y \
		--ignore=$(IGNORE) \
		$(SRC)

# -----------------------------------------
# Combined check (format + lint)
# -----------------------------------------
check: format lint

# -----------------------------------------
# Dry-run (CI friendly, does NOT modify files)
# -----------------------------------------
format-check:
	@echo "Checking formatting (no changes)..."
	$(BLACK) --check $(SRC)

lint-ci:
	@echo "Running Pylint (CI mode)..."
	$(PYLINT) --rcfile=.pylintrc \
		--recursive=y \
		--ignore=$(IGNORE) \
		$(SRC)

# -----------------------------------------
# CI task (dry-run formatting + Pylint)
# -----------------------------------------
ci: format-check lint-ci


# -----------------------------------------
# Run pipeline
# -----------------------------------------
run:
	@echo "==> Checking database..."
	python scripts/init_db.py

	@echo "==> Synchronizing Clash Royale data..."
	python scripts/collect_data.py

	@echo "==> Launching dashboard..."
	python -m streamlit run dashboard/home.py

# Default directory is the current one
DIR ?= .
# make tree DIR="./models/" for exemple to change
tree:
	@echo "Displaying the project's tree in $(DIR):"
	tree $(DIR) -I ".venv|__pycache__|.git|clash_royale_manager.egg-info|migrations/|.vscode|data|logs|secrets|*.sqlite"

# -----------------------------------------
# Commit (only if checks )
# -----------------------------------------
commit:
	@echo "Running checks before commit..."
	@$(MAKE) check || { \
		echo "\033[1;31m❌ Checks failed — commit blocked!\033[0m"; \
		exit 1; \
	}
	@echo "\033[1;32m✅ Checks passed — starting commit helper\033[0m"; 
	@while true; do \
		~/bin/git-commit-helper; \
		read -p "Do you want to commit more changes? (y/N) " continue_answer; \
		case $$continue_answer in \
			[Yy]*) echo "Continuing with next commit..."; ;; \
			*) echo "Done committing."; break ;; \
		esac; \
	done

clean:
	@echo "Cleaning cache files..."

	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name "cache" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete

	@echo "Clean complete."

clean-db:
	@read -p "Delete SQLite database? [y/N] " ans && \
	([ "$$ans" = "y" ] || [ "$$ans" = "Y" ]) || exit 1

	@echo "Removing database..."
	@rm -f data/clan_manager.db

	@echo "Database removed."

reset-db:
	@read -p "FULL RESET: database, migrations, and cache will be deleted. Continue? [y/N] " ans && \
	([ "$$ans" = "y" ] || [ "$$ans" = "Y" ]) || exit 1

	@echo "Step 1: cleaning cache..."
	@$(MAKE) clean

	@echo "Step 2: removing database..."
	@rm -f data/clan_manager.db

	@echo "Step 3: removing migration versions..."
	@find app/database/migrations/versions \
		-type f \
		-name "*.py" \
		-not -name "__init__.py" \
		-not -name ".gitkeep" \
		-delete

	@echo "Step 4: generating initial migration..."
	@alembic revision --autogenerate -m "initial schema"

	@echo "Step 5: applying migration..."
	@alembic upgrade head

	@echo "RESET COMPLETE."

dev:
	@echo "Building and starting application..."
	@UID=$$(id -u) GID=$$(id -g) docker compose up --build

start:
	@echo "Building and starting application in background..."
	@UID=$$(id -u) GID=$$(id -g) docker compose up --build -d

stop:
	@UID=$$(id -u) GID=$$(id -g) docker compose down
