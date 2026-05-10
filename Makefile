UV = uv
PYTHON = $(UV) run python
MAIN_SCRIPT = main.py

.PHONY: install run debug clean lint lint-strict

install:
	$(UV) sync

run: install
	$(PYTHON) $(MAIN_SCRIPT) $(ARG)

debug:
	$(PYTHON) -m pdb $(MAIN_SCRIPT)

clean:
	rm -rf .venv
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	$(UV) run flake8 . --exclude .venv
	$(UV) run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs