import pytest

from pyppl import Proc, Box, ProcSet
from pyppl.proctree import ProcNode, ProcTree
from pyppl.exception import ProcTreeProcExists, ProcTreeParseError#, ProcHideError

@pytest.fixture(autouse = True)
def resetNodes():
	ProcTree.NODES = {}
	yield

@pytest.fixture
def set1():
	p15 = Proc()
	p16 = Proc()
	p17 = Proc()
	p18 = Proc()
	p19 = Proc()
	p20 = Proc()
	#        hide
	# p15 -> p16  ->  p17 -> 19
	#         \_ p18_/  \_ p20
	#p16.hide = True
	p20.depends = p17
	p19.depends = p17
	p17.depends = p16, p18
	p18.depends = p16
	p16.depends = p15
	ProcTree.register(p15)
	return Box(p15 = p15, p16 = p16, p17 = p17, p18 = p18, p19 = p19, p20 = p20)

@pytest.fixture(scope = 'function')
def set2():
	p14 = Proc()
	p15 = Proc()
	p16 = Proc()
	p17 = Proc()
	p18 = Proc()
	p19 = Proc()
	p20 = Proc()
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	#p18.hide = True
	p20.depends = p17
	p19.depends = p17
	p17.depends = p16, p18
	p18.depends = p16
	p16.depends = p14, p15
	ProcTree.register(p14, p15)
	return Box(p15 = p15, p16 = p16, p17 = p17, p18 = p18, p19 = p19, p20 = p20, p14 = p14)

def test_procnode():
	# init
	p1 = Proc()
	pn = ProcNode(p1)
	assert pn.proc is p1
	assert pn.prev == []
	assert pn.next == []
	assert pn.ran == False
	assert pn.start == False

	p2 = Proc(id = 'p1')
	assert pn.sameIdTag(p2)

	assert repr(pn).startswith('<ProcNode(<Proc(id=p1,tag=notag) @')

def test_proctree_init():
	p21 = Proc()
	p22 = Proc()
	p23 = Proc()
	p24 = Proc()
	p25 = Proc()
	p23.depends = p21, p22
	#p23.hide    = True
	p24.depends = p23
	p25.depends = p23
	ProcTree.register(p21)
	ProcTree.register(p22)

	pt = ProcTree()
	pt.init()
	# with pytest.raises(ProcHideError):
	# 	pt.init()
	assert p21 in ProcTree.NODES
	assert p22 in ProcTree.NODES
	assert p23 in ProcTree.NODES
	assert p24 in ProcTree.NODES
	assert p25 in ProcTree.NODES
	assert ProcTree.NODES[p21].prev == []
	assert ProcTree.NODES[p22].prev == []
	assert ProcTree.NODES[p23].prev == [ProcTree.NODES[p21], ProcTree.NODES[p22]]
	assert ProcTree.NODES[p24].prev == [ProcTree.NODES[p23]]
	assert ProcTree.NODES[p25].prev == [ProcTree.NODES[p23]]
	assert ProcTree.NODES[p21].next == [ProcTree.NODES[p23]]
	assert ProcTree.NODES[p22].next == [ProcTree.NODES[p23]]
	assert ProcTree.NODES[p23].next == [ProcTree.NODES[p24], ProcTree.NODES[p25]]
	assert ProcTree.NODES[p24].next == []
	assert ProcTree.NODES[p25].next == []


def test_proctree_register():
	p3 = Proc()
	ProcTree.register(p3)
	del ProcTree.NODES[p3]
	ProcTree.register(p3)
	assert ProcTree.NODES[p3].proc is p3

def test_proctree_check():
	p4 = Proc()
	p5 = Proc(id = 'p4')
	ProcTree.register(p4)
	ProcTree.register(p5)
	with pytest.raises(ProcTreeProcExists):
		ProcTree.check(p4)

def test_proctree_getprevstr():
	p6 = Proc()
	p7 = Proc()
	p7.depends = p6
	ProcTree.register(p6)
	ProcTree().init()
	assert ProcTree.getPrevStr(p6) == 'START'
	assert ProcTree.getPrevStr(p7) == '[p6]'

def test_proctree_getnextstr():
	p8 = Proc()
	p9 = Proc()
	p9.depends = p8
	ProcTree.register(p8)
	ProcTree().init()
	assert ProcTree.getNextStr(p8) == '[p9]'
	assert ProcTree.getNextStr(p9) == 'END'

def test_proctree_getnext_and_reset():
	p10 = Proc()
	p11 = Proc()
	p11.depends = p10
	ProcTree.register(p10)
	ProcTree().init()
	assert ProcTree.getNext(p10) == [p11]
	assert ProcTree.getNext(p11) == []

	ProcTree.reset()
	ProcTree.NODES[p10].prev == []
	ProcTree.NODES[p10].next == []
	ProcTree.NODES[p11].prev == []
	ProcTree.NODES[p11].next == []
	ProcTree.NODES[p10].ran == False
	ProcTree.NODES[p10].start == False
	ProcTree.NODES[p11].ran == False
	ProcTree.NODES[p11].start == False

def test_proctree_setgetstarts():
	p12 = Proc()
	p13 = Proc()
	p14 = Proc()
	#p14.hide = True
	p12.depends = p13
	ProcTree.register(p13)
	ProcTree.register(p14)
	pt = ProcTree()
	pt.init()
	# with pytest.raises(ProcHideError):
	# 	pt.setStarts([p14])
	pt.ends = [1,2,3]
	pt.setStarts([p13])
	assert ProcTree.NODES[p12].start == False
	assert ProcTree.NODES[p13].start == True
	assert ProcTree.NODES[p14].start == False
	assert pt.starts == [p13]
	assert pt.ends == []

	pt.starts = []
	assert pt.getStarts() == [p13]
	assert pt.starts == [p13]
	assert pt.getStarts() == [p13]

def test_proctree_getpaths(set1):
	#        hide
	# p15 -> p16  ->  p17 -> 19
	#         \_ p18_/  \_ p20
	pt = ProcTree()
	pt.init()
	assert pt.getPaths(set1.p15) == []
	assert pt.getPaths(set1.p19) == [
		[set1.p17, set1.p16, set1.p15], [set1.p17, set1.p18, set1.p16, set1.p15]]
	assert pt.getPaths(set1.p20) == [
		[set1.p17, set1.p16, set1.p15], [set1.p17, set1.p18, set1.p16, set1.p15]]
	# assert pt.getPaths(set1.p19, check_hide = True)  == [
	# 	[set1.p17, set1.p15], [set1.p17, set1.p18, set1.p15]]
	# assert pt.getPaths(set1.p20, check_hide = True)  == [
	# 	[set1.p17, set1.p15], [set1.p17, set1.p18, set1.p15]]

	# circulic dependence
	p21 = Proc()
	p22 = Proc()
	p23 = Proc()
	# p21 -> p22 -> p23 -> p21
	p21.depends = p23
	p23.depends = p22
	p22.depends = p21
	pt = ProcTree()
	pt.init()
	with pytest.raises(ProcTreeParseError):
		pt.getPaths(p23)

def test_proctree_getpathstostarts(set2):
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	pt = ProcTree()
	pt.init()
	pt.setStarts([set2.p15])
	assert pt.getPathsToStarts(set2.p15) == []
	assert pt.getPathsToStarts(set2.p19) == [[set2.p17, set2.p16, set2.p15], [set2.p17, set2.p18, set2.p16, set2.p15]]
	assert pt.getPathsToStarts(set2.p20) == [[set2.p17, set2.p16, set2.p15], [set2.p17, set2.p18, set2.p16, set2.p15]]
	# assert pt.getPathsToStarts(set2.p19, check_hide = True) == [[set2.p17, set2.p16, set2.p15]]
	# assert pt.getPathsToStarts(set2.p20, check_hide = True) == [[set2.p17, set2.p16, set2.p15]]

	pt.setStarts([set2.p14, set2.p15])
	assert pt.getPathsToStarts(set2.p14) == []
	assert pt.getPathsToStarts(set2.p15) == []
	assert pt.getPathsToStarts(set2.p16) == [[set2.p14], [set2.p15]]
	assert pt.getPathsToStarts(set2.p18) == [[set2.p16, set2.p14], [set2.p16, set2.p15]]
	assert pt.getPathsToStarts(set2.p17) == [
		[set2.p16, set2.p14],
		[set2.p16, set2.p15],
		[set2.p18, set2.p16, set2.p14],
		[set2.p18, set2.p16, set2.p15],
	]
	assert pt.getPathsToStarts(set2.p19) == [
		[set2.p17, set2.p16, set2.p14],
		[set2.p17, set2.p16, set2.p15],
		[set2.p17, set2.p18, set2.p16, set2.p14],
		[set2.p17, set2.p18, set2.p16, set2.p15],
	]
	assert pt.getPathsToStarts(set2.p20) == [
		[set2.p17, set2.p16, set2.p14],
		[set2.p17, set2.p16, set2.p15],
		[set2.p17, set2.p18, set2.p16, set2.p14],
		[set2.p17, set2.p18, set2.p16, set2.p15],
	]
	# assert pt.getPathsToStarts(set2.p17, check_hide = True) == [[set2.p16, set2.p14], [set2.p16, set2.p15]]
	# assert pt.getPathsToStarts(set2.p19, check_hide = True) == [[set2.p17, set2.p16, set2.p14], [set2.p17, set2.p16, set2.p15]]
	# assert pt.getPathsToStarts(set2.p20, check_hide = True) == [[set2.p17, set2.p16, set2.p14], [set2.p17, set2.p16, set2.p15]]

def test_proctree_chechpath(set2):
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	pt = ProcTree()
	pt.init()
	assert pt.checkPath(set2.p16) == [set2.p14]
	pt.setStarts([set2.p14])
	assert pt.checkPath(set2.p16) == [set2.p15]
	pt.setStarts([set2.p14, set2.p15])
	assert pt.checkPath(set2.p16) is True

def test_proctree_getends(set2):

	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	pt = ProcTree()
	pt.init()
	pt.setStarts([set2.p14, set2.p15])
	assert set(pt.getEnds()) == {set2.p19, set2.p20}
	assert set(pt.ends) == {set2.p19, set2.p20}
	assert set(pt.getEnds()) == {set2.p19, set2.p20}

	#set2.p19.hide = True
	pt.ends = []
	# with pytest.raises(ProcHideError):
	# 	pt.getEnds()

def test_proctree_getends_failed():
	p1 = Proc()
	p2 = Proc()
	p2.depends = p1
	ProcTree.register(p1)
	pt = ProcTree()
	pt.init()
	with pytest.raises(ProcTreeParseError):
		#Failed to determine end processes by start processes
		pt.getEnds()

	p3 = Proc()
	p3.depends = p2
	pt = ProcTree()
	pt.init()
	pt.setStarts([p3])
	with pytest.raises(ProcTreeParseError):
		# Failed to determine end processes, one of the paths cannot go through: 'p3 <- p2 <- p1'
		pt.getEnds()

def test_proctree_getallpaths(set2):
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#         ##hide moved to plugin
	pt = ProcTree()
	pt.init()
	pt.setStarts([set2.p14, set2.p15])
	allpath = list(pt.getAllPaths())
	assert len(allpath) == 8
	assert [set2.p19, set2.p17, set2.p16, set2.p14] in allpath
	assert [set2.p19, set2.p17, set2.p16, set2.p15] in allpath
	assert [set2.p20, set2.p17, set2.p16, set2.p14] in allpath
	assert [set2.p20, set2.p17, set2.p16, set2.p15] in allpath
	assert [set2.p19, set2.p17, set2.p18, set2.p16, set2.p14] in allpath
	assert [set2.p19, set2.p17, set2.p18, set2.p16, set2.p15] in allpath
	assert [set2.p20, set2.p17, set2.p18, set2.p16, set2.p14] in allpath
	assert [set2.p20, set2.p17, set2.p18, set2.p16, set2.p15] in allpath

def test_proctree_getallpaths_single():
	p1 = Proc()
	ProcTree.register(p1)
	pt = ProcTree()

	pt.setStarts([p1])
	assert list(pt.getAllPaths()) == [[p1]]

def test_proctree_getnexttorun(set2):
	# p15 -> p16  ->  p17 -> 19
	# p14 _/  \_ p18_/  \_ p20
	#           hide
	p1 = Proc()
	#ProcTree.register(p1)
	p2 = Proc()
	p2.depends = p1
	pt = ProcTree()
	pt.init()
	pt.setStarts([set2.p14, set2.p15])
	pt.NODES[set2.p14].ran = True
	assert pt.getNextToRun() is set2.p15
	pt.NODES[set2.p15].ran = True
	assert pt.getNextToRun() is set2.p16
	pt.NODES[set2.p16].ran = True
	assert pt.getNextToRun() is set2.p18
	pt.NODES[set2.p18].ran = True
	assert pt.getNextToRun() is set2.p17
	pt.NODES[set2.p17].ran = True
	assert pt.getNextToRun() is set2.p20
	pt.NODES[set2.p20].ran = True
	assert pt.getNextToRun() is set2.p19
	pt.NODES[set2.p19].ran = True
	assert pt.getNextToRun() is None
