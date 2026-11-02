PYTHON ?= python3.12
VENV ?= .venv
RUN = $(VENV)/bin/python

.PHONY: install install-test test dev dev-tavus eval
install:
	$(PYTHON) -m venv $(VENV)
	$(RUN) -m pip install -e '.[test,realtime]'

install-test:
	$(PYTHON) -m venv $(VENV)
	$(RUN) -m pip install -e '.[test]'

test:
	$(RUN) -m pytest

# These commands deliberately fail until the corresponding implementation is ready.
dev dev-tavus eval:
	@echo '$@ unavailable: foundation only; see docs/STATUS.md and approval gates.'
	@exit 1
