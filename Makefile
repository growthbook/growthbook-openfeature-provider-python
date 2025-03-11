.PHONY: clean clean-test clean-build clean-pyc help lint test test-cov format install dev-install

help:
	@echo "Commands:"
	@echo "clean - remove all build, test, and coverage artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests"
	@echo "test-cov - run tests with coverage report"
	@echo "format - format code with black and isort"
	@echo "install - install the package"
	@echo "dev-install - install the package in development mode"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

lint:
	flake8 src tests

test:
	pytest

test-cov:
	pytest --cov=src/growthbook_openfeature_provider tests/

format:
	black src tests
	isort src tests

install:
	pip install .

dev-install:
	pip install -e ".[dev]" 