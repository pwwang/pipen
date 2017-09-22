SHELL=bash
PYTHON=python

.PHONY: test api build dist

test: ./tests/*.py
	@wd=`pwd`;                                \
	cd ./tests;                               \
	for tfile in test*.py; do                 \
		echo "";                              \
		echo "Running test: python $$tfile";  \
		echo '----------------------------------------------------------------------'; \
		python $$tfile;                       \
		echo "";                              \
		echo "Running test: python3 $$tfile"; \
		echo '----------------------------------------------------------------------'; \
		python3 $$tfile;                      \
	done;                                     \
	cd $$wd 

api:
	$(PYTHON) ./api.py

build:
	$(PYTHON) setup.py build --force

dist:
	$(PYTHON) setup.py sdist upload	
