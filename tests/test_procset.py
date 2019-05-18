
from pyppl import Box
from pyppl.procset import _Proxy

pytest_plugins = ["tests.fixt_procset"]

def test_proxy():
	p = _Proxy([1,2,3,4,1])
	assert p.count(1) == 2
	assert p.denominator == [1] * 5

	p1 = _Proxy([Box(), Box(), Box()])
	p1.x = (1,2)
	assert p1[0].x == 1
	assert p1[1].x == 2
	assert 'x' not in p1[2]

	p1.y = 3
	assert p1[0].y == 3
	assert p1[1].y == 3
	assert p1[2].y == 3

	p2 = p1[:2]
	assert len(p2) == 2
	assert p2[0] is p1[0]
	assert p2[1] is p1[1]

	assert p1['y'] == [3,3,3]

	p2[0] = Box(a = 1)
	assert p2[0].a == 1

	p2['y'] = 1
	assert p2['y'] == [1,1]

def test_proxy_add():
	p = _Proxy([1,2,3,4])
	p2 = _Proxy([1,2,5])
	p.add(p2)
	assert p == [1,2,3,4,5]