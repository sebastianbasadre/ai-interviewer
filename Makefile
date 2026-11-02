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

dev:
	APP_MODE=mock AVATAR_MODE=mock $(RUN) -m ai_interviewer

eval:
	$(RUN) -m evals.run_evals

dev-tavus:
	@echo 'Tavus unavailable: provider integration and explicit G4 approval required.'
	@exit 1
