UV := uv run --prerelease=allow

.PHONY: install build test lint format typecheck all run demo video shots clean

install:        ## Install dependencies (dev group + demo extra)
	uv sync --all-extras --prerelease=allow

build:          ## Build wheel + sdist into dist/
	uv build

test:           ## Run the test suite
	$(UV) pytest

lint:           ## Lint with Ruff
	$(UV) ruff check .

format:         ## Auto-format with Ruff
	$(UV) ruff format .

typecheck:      ## Static type-check with mypy
	$(UV) mypy agentcanvas viz.py assets/scripts/main.py assets/scripts/make_demo.py assets/scripts/make_screenshots.py

all: lint typecheck test   ## Lint + typecheck + test

run:            ## Build the report from the latest Logfire run
	$(UV) python viz.py

demo:           ## Generate a sample agent run (writes telemetry to Logfire)
	$(UV) python assets/scripts/main.py

video:          ## Record the guided-tour demo MP4 (needs Chrome + ffmpeg)
	$(UV) python assets/scripts/make_demo.py

shots:          ## Capture panel screenshots into assets/ (needs Chrome)
	$(UV) python assets/scripts/make_screenshots.py

clean:          ## Remove generated artifacts and caches
	rm -f agent_flow.html
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__
