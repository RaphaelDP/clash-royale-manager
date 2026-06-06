# =========================================
# Project: clash-royale-manager
# Purpose: Formatting & linting utilities
# =========================================

# Python executable (assumes venv is activated)
PYTHON := python

# Tools (resolved from active environment)
BLACK := black
PYLINT := pylint

# Project paths
SRC := dashboard app scripts tests

# Files and directories to ignore
IGNORE := venv,.venv,__pycache__,.git,logs,data,secrets

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
launch:
	@echo "Launching Streamlit GUI..."
	python -m streamlit run dashboard/home.py


# Default directory is the current one
DIR ?= .
# make tree DIR="./models/" for exemple to change
tree:
	@echo "Displaying the project's tree in $(DIR):"
	tree $(DIR) -I ".venv|__pycache__|.git|"

# -----------------------------------------
# Commit (only if checks )
# -----------------------------------------
commit:
	@echo "Running checks before commit..."
	@$(MAKE) check || { \
		echo "\033[1;31m❌ Checks failed — commit blocked!\033[0m"; \
		exit 1; \
	}
	@echo "\033[1;32m✅ Checks ed — starting commit helper\033[0m"; 
	@while true; do \
		~/bin/git-commit-helper; \
		read -p "Do you want to commit more changes? (y/N) " continue_answer; \
		case $$continue_answer in \
			[Yy]*) echo "Continuing with next commit..."; ;; \
			*) echo "Done committing."; break ;; \
		esac; \
	done