SHELL=bash

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
	