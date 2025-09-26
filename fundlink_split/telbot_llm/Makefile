# Makefile

.PHONY: install lint test run

install:
	pip install -r requirements.txt

lint:
	mypy telbot_llm
	flake8 telbot_llm

test:
	pytest tests

run:
	python scripts/run_dev.py