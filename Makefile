SHELL=bash
PYTHON=python

.PHONY: example exampes api

example:
	@wd=`pwd`;                                                                         \
	for t in ./examples/*; do                                                          \
		echo "";                                                                       \
		echo "Running example in $$t";                                                 \
		echo '----------------------------------------------------------------------'; \
		cd $$t;                                                                        \
		for p in *.py; do                                                              \
			if [[ "$$p" == "differentRunner.py" ]]; then                               \
				continue;                                                              \
			elif [[ "$$p" == "useParams.py" ]]; then                                   \
				$(PYTHON) $$p --datadir ./data;                                        \
				if [[ $$? -ne 0 ]]; then exit 1; fi;                                   \
			else                                                                       \
				echo "> $(PYTHON) $$p";                                                \
				echo "";                                                               \
				$(PYTHON) $$p;                                                         \
				if [[ $$? -ne 0 ]]; then exit 1; fi;                                   \
			fi;                                                                        \
		done;                                                                          \
		cd $$wd;                                                                       \
	done

examples: example

api:
	$(PYTHON) ./api.py
