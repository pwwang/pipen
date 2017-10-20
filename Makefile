SHELL=bash
PYTHON=python
PYTHON3=python3

.PHONY: test api build dist

test: ./tests/*.py
	@wd=`pwd`;                                                                         \
	cd ./tests;                                                                        \
	for tfile in test*.py; do                                                          \
		echo "";                                                                       \
		echo "Running test: $(PYTHON) $$tfile";                                        \
		echo '----------------------------------------------------------------------'; \
		$(PYTHON) $$tfile;                                                             \
		echo "";                                                                       \
		echo "Running test: $(PYTHON3) $$tfile";                                       \
		echo '----------------------------------------------------------------------'; \
		$(PYTHON3) $$tfile;                                                            \
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
				$(PYTHON3) $$p --param-datadir ./data;                                 \
			else                                                                       \
				$(PYTHON) $$p;                                                         \
				$(PYTHON3) $$p;                                                        \
			fi;                                                                        \
		done;                                                                          \
		cd $$wd;                                                                       \
	done

tutorials: tutorial

api:
	$(PYTHON) ./api.py

build:
	$(PYTHON) setup.py build --force

dist:
	$(PYTHON) setup.py sdist upload	
