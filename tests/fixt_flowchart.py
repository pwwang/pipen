import pytest
from pyppl import Proc

@pytest.fixture
def p1():
	return Proc('p1')

@pytest.fixture
def p2():
	return Proc('p2')

@pytest.fixture
def p3():
	return Proc('p3')

@pytest.fixture
def p4():
	return Proc('p4')

@pytest.fixture
def p_procset1():
	p = Proc('p_procset1')
	p.config.tag = 'notag@procset1'
	return p

@pytest.fixture
def p_procset2():
	p = Proc('p_procset2')
	p.config.tag = 'notag@procset2'
	return p

@pytest.fixture
def p_procset3():
	p = Proc('p_procset3')
	p.config.tag = 'notag@p_procset3'
	return p

@pytest.fixture
def p_tag_1st():
	return Proc('p_tag_1st', tag = '1st')

@pytest.fixture
def p_desc():
	return Proc('p_desc', desc = 'The description of p')

@pytest.fixture
def p_skipplus():
	return Proc('p_skipplus', resume = 'skip+')

@pytest.fixture
def p_exdir():
	return Proc('p_exdir', exdir = '.')

@pytest.fixture
def p_procset1_skipplus():
	p = Proc('p_procset1_skipplus', resume = 'skip+')
	p.config.tag = 'notag@procset1'
	return p

@pytest.fixture
def p_procset2_exdir():
	p = Proc('p_procset2_exdir', exdir = '.')
	p.config.tag = 'notag@procset2'
	return p

@pytest.fixture
def procs(p1, p2, p3, p4, p_procset1, p_procset2, p_procset3,
	p_tag_1st, p_desc, p_skipplus, p_exdir, p_procset1_skipplus, p_procset2_exdir):
	return dict(
		p1                  = p1,
		p2                  = p2,
		p3                  = p3,
		p4                  = p4,
		p_procset1          = p_procset1,
		p_procset2          = p_procset2,
		p_procset3          = p_procset3,
		p_tag_1st           = p_tag_1st,
		p_desc              = p_desc,
		p_skipplus          = p_skipplus,
		p_procset1_skipplus = p_procset1_skipplus,
		p_procset2_exdir    = p_procset2_exdir,
		p_exdir             = p_exdir)