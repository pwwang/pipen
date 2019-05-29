import pytest
from pyppl.channel import Channel

@pytest.mark.parametrize('obj, expt', [
	('', ('', )),
	([], ([], )),
	(1, (1, )),
	((1,2,3), (1,2,3)),
])
def test_cleanup(obj, expt):
	assert Channel._tuplize(obj) == expt

@pytest.mark.parametrize('obj, expt', [
	(1,     [(1, )]),
	("a,b", [("a,b", )]),
	(["a", "b"], [("a", ), ("b", )]),
	(("a", "b"), [("a", "b")]),
	([], []),
	([[]], [([], )]),
	# issue #29
	('', [('', )])
])
def test_create(obj, expt):
	assert Channel.create(obj) == expt

def test_create_exc():
	with pytest.raises(ValueError):
		Channel.create([("a", ), ("c", "d")])

