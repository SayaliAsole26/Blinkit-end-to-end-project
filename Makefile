.PHONY: install install-dev test lint config-check ingest pipeline clean-embed dashboard clean

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src tests

config-check:
	$(PYTHON) -m pytest tests/test_config.py -v

ingest:
	$(PYTHON) -m pipeline ingest --help

pipeline:
	$(PYTHON) scripts/run_pipeline.py --help

clean-embed:
	$(PYTHON) -m pipeline run --stage clean_embed --run-id $(or $(RUN_ID),run_001)

cluster-label:
	$(PYTHON) -m pipeline run --stage cluster_label --run-id $(or $(RUN_ID),run_001) --segments-run-id $(or $(SEGMENTS_RUN_ID),$(or $(RUN_ID),run_001))

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]"
