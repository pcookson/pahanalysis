SHELL := /bin/bash

VENV_DIR := server/.venv
VENV_PY := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000

.PHONY: setup dev clean

setup:
	@cd server && \
		if [ -d .venv ] && [ ! -f .venv/bin/activate ]; then \
			echo "Removing incomplete virtual environment at server/.venv"; \
			rm -rf .venv; \
		fi && \
		if [ ! -d .venv ]; then python3 -m venv .venv; fi && \
		if [ ! -f .venv/bin/activate ]; then \
			echo "Virtual environment creation failed (missing .venv/bin/activate)."; \
			echo "On Debian/Ubuntu, install the OS package for venv support (for example: python3.12-venv)."; \
			exit 1; \
		fi && \
		. .venv/bin/activate && \
		pip install -r requirements.txt

dev: $(VENV_PY)
	@mkdir -p .tmp
	@echo "Starting backend on http://localhost:$(BACKEND_PORT) and frontend on http://localhost:$(FRONTEND_PORT)"
	@echo "Press Ctrl+C to stop both processes"
	@trap 'kill 0' INT TERM EXIT; \
		(cd server && ../$(VENV_PY) -m http.server $(BACKEND_PORT)) & \
		(cd web && ../$(VENV_PY) -m http.server $(FRONTEND_PORT)) & \
		wait

$(VENV_PY):
	@$(MAKE) setup

clean:
	@rm -rf server/.venv
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -rf web/node_modules node_modules dist
