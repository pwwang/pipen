import pytest
from pyppl import Job

pytest_plugins = ["tests.fixt_job"]

# use RunnerTest to pass the name check
class RunnerTest(Job):
	pass



