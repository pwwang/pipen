SHELL=bash
PYTHON=python
PYTHON2=python2
PYTHON3=python3

.PHONY: test test2 test3 tutorial tutorials cov covupload coverage api build dist 

test: ./tests/*.py
	@wd=`pwd`;                                                                         \
	cd ./tests;                                                                        \
	for tfile in test*.py; do                                                          \
		echo "";                                                                       \
		echo "Running test: $(PYTHON) $$tfile";                                        \
		echo '----------------------------------------------------------------------'; \
		$(PYTHON) $$tfile;                                                             \
		if [[ $$? -ne 0 ]]; then exit 1; fi;                                           \
	done;                                                                              \
	cd $$wd 

test2: ./tests/*.py
	@wd=`pwd`;                                                                         \
	cd ./tests;                                                                        \
	for tfile in test*.py; do                                                          \
		echo "";                                                                       \
		echo "Running test: $(PYTHON2) $$tfile";                                        \
		echo '----------------------------------------------------------------------'; \
		$(PYTHON2) $$tfile;                                                             \
		if [[ $$? -ne 0 ]]; then exit 1; fi;                                           \
	done;                                                                              \
	cd $$wd 

test3: ./tests/*.py
	@wd=`pwd`;                                                                         \
	cd ./tests;                                                                        \
	for tfile in test*.py; do                                                          \
		echo "";                                                                       \
		echo "Running test: $(PYTHON3) $$tfile";                                       \
		echo '----------------------------------------------------------------------'; \
		$(PYTHON3) $$tfile;                                                            \
		if [[ $$? -ne 0 ]]; then exit 1; fi;                                           \
	done;                                                                              \
	cd $$wd 

tutorial:
	@wd=`pwd`;                                                                         \
	for t in ./tutorials/*; do                                                         \
		echo "";                                                                       \
		echo "Running tutorial: $$t";                                                  \
		echo '----------------------------------------------------------------------'; \
		cd $$t;                                                                        \
		for p in *.py; do                                                              \
			if [[ "$$p" == "differentRunner.py" ]]; then                               \
				continue;                                                              \
			elif [[ "$$p" == "useParams.py" ]]; then                                   \
				$(PYTHON) $$p --param-datadir ./data;                                  \
				if [[ $$? -ne 0 ]]; then exit 1; fi;                                   \
			else                                                                       \
				$(PYTHON) $$p;                                                         \
				if [[ $$? -ne 0 ]]; then exit 1; fi;                                   \
			fi;                                                                        \
		done;                                                                          \
		cd $$wd;                                                                       \
	done

tutorials: tutorial

cov:
	@wd=`pwd`;                                                                        \
	cd ./tests;                                                                       \
	for tfile in test*.py; do                                                         \
		echo -e "\nRUNNING TESTS: $$tfile";                                           \
		echo      "=================================================================";\
		coverage run -a --concurrency=multiprocessing $$tfile;                        \
		coverage combine;                                                             \
	done;                                                                             \
	coverage xml;                                                                     \
	coverage html;                                                                    \
	coverage report;                                                                  \
	echo -e "\nRun 'make covupload' to upload the results if coverage is satisfied."; \
	cd $$wd

covupload:
	python-codacy-coverage -r tests/coverage.xml                

coverage: cov

api:
	$(PYTHON) ./api.py

build:
	$(PYTHON) setup.py sdist bdist_wheel --universal

dist:
	twine upload --skip-existing dist/* 
