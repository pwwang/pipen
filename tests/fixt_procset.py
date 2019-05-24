
import pytest
from pyppl import Proc
from pyppl.procset import Proxy, Values, PSProxy, ProcSet

@pytest.fixture
def pProc1():
	return Proc('pProc1')

@pytest.fixture
def pProc2():
	return Proc('pProc2')

@pytest.fixture
def pProc3():
	return Proc('pProc3')

@pytest.fixture
def empty_psp():
	return PSProxy(procset = ProcSet())


@pytest.fixture
def psp3(pProc1, pProc2, pProc3):
	return PSProxy(procset = ProcSet(pProc1, pProc2, pProc3))

@pytest.fixture
def empty_ps():
	return ProcSet(id = 'empty_ps')

@pytest.fixture
def ps3_depends(pProc1, pProc2, pProc3):
	return ProcSet(pProc1, pProc2, pProc3, id = 'ps3_depends', depends = True, copy = False)

@pytest.fixture
def ps3_copy(pProc1, pProc2, pProc3):
	return ProcSet(pProc1, pProc2, pProc3, id = 'ps3_copy', depends = False, copy = True)

@pytest.fixture
def ps3_copy_depends(pProc1, pProc2, pProc3):
	return ProcSet(pProc1, pProc2, pProc3, id = 'ps3_copy_depends', depends = True, copy = True)

@pytest.fixture
def ps3(pProc1, pProc2, pProc3):
	return ProcSet(pProc1, pProc2, pProc3, id = 'ps3', depends = False, copy = False)

