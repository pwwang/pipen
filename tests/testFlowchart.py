import path, unittest

import sys
import tempfile
from copy import copy
from os import path
from pyppl.flowchart import Flowchart

def which(program):
	import os
	def is_exe(fpath):
		return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

	fpath, _ = os.path.split(program)
	if fpath:
		if is_exe(program):
			return program
	else:
		for path in os.environ["PATH"].split(os.pathsep):
			path = path.strip('"')
			exe_file = os.path.join(path, program)
			if is_exe(exe_file):
				return exe_file

	return None

class Node(object):
	def __init__(self, name, aggr = '', exdir = '', resume = ''):
		self._name = name
		self.aggr  = aggr
		self.exdir = exdir
		self.resume = resume

	def name(self, full = False):
		return self._name

class TestFlowchart (unittest.TestCase):

	def testInit(self):
		fc = Flowchart()
		self.assertIsInstance(fc, Flowchart)
		self.assertEqual(fc.fcfile, path.splitext(sys.argv[0])[0] + '.pyppl.svg')
		self.assertEqual(fc.dotfile, path.splitext(sys.argv[0])[0] + '.pyppl.dot')
		self.assertEqual(fc.command, ['dot', '-Tsvg', fc.dotfile, '-o', fc.fcfile])
		self.assertEqual(fc.theme, Flowchart.THEMES['default'])
		self.assertEqual(fc.nodes, [])
		self.assertEqual(fc.starts, [])
		self.assertEqual(fc.ends, [])
		self.assertEqual(fc.links, [])
		self.assertEqual(fc.nodes, [])
		self.assertEqual(fc.groups, {})
	
	def testSetTheme(self):
		fc = Flowchart()
		theme = {'base': { 'style': 'filled' }}
		fc.setTheme({'base': { 'style': 'filled' }})
		self.assertEqual(fc.theme, theme)
		fc.setTheme('dark')
		self.assertEqual(fc.theme, Flowchart.THEMES['dark'])
	
	def testAddNodeLink(self):
		fc = Flowchart()
		n1 = Node('n1')
		n2 = Node('n2', aggr = 'g1')
		n3 = Node('n3', aggr = 'g1')
		fc.addNode(n1)
		fc.addNode(n2, 'start')
		fc.addNode(n3, 'end')
		self.assertEqual(len(fc.nodes), 3)
		self.assertIs(fc.nodes[0], n1)
		self.assertIs(fc.nodes[1], n2)
		self.assertIs(fc.nodes[2], n3)
		self.assertEqual(len(fc.starts), 1)
		self.assertIs(fc.starts[0], n2)
		self.assertEqual(len(fc.ends), 1)
		self.assertIs(fc.ends[0], n3)
		self.assertEqual(fc.groups, {'g1': [n2, n3]})
		fc.addLink(n1, n2)
		fc.addLink(n2, n3)
		self.assertEqual(len(fc.links), 2)
		self.assertEqual(fc.links[0], (n1, n2))
		self.assertEqual(fc.links[1], (n2, n3))
		fc.addLink(n2, n1)
		self.assertEqual(len(fc.links), 3)

	# helper function
	def assertInDot(self, name, theme, nodelines):
		import re
		if not isinstance(nodelines, list):
			nodelines.splitlines()
		expr = r'"%s"\s\[.*%s="%s".*\]'
		for key, val in theme.items():
			found = False
			ex = expr % (name, key, val)
			for line in nodelines:
				if re.search(ex, line):
					found = True
					break
			if not found:
				self.fail("Theme not found.\n>>> Theme:\n  %s \n>>> In:\n  %s" % ('\n  '.join(['%-10s: %s' % (k, theme[k]) for k in sorted(theme.keys())]), '\n  '.join(nodelines) + '\n'))

	def testDotNodes(self):

		fc = Flowchart()
		n1 = Node('n1')
		fc.nodes.append(n1)
		nodestr = fc._dotnodes()
		self.assertInDot('n1', Flowchart.THEMES['default']['base'], nodestr)

		basetheme = copy(Flowchart.THEMES['default']['base'])

		fc.starts.append(n1)
		starttheme = copy(basetheme)
		starttheme.update(Flowchart.THEMES['default']['start'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', starttheme, nodestr)

		fc.starts = []
		fc.ends.append(n1)
		endtheme = copy(basetheme)
		endtheme.update(Flowchart.THEMES['default']['end'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', endtheme, nodestr)

		fc.ends = []
		n1.exdir = 'a'
		extheme = copy(basetheme)
		extheme.update(Flowchart.THEMES['default']['export'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', extheme, nodestr)

		n1.exdir = ''
		n1.resume = True
		restheme = copy(basetheme)
		restheme.update(Flowchart.THEMES['default']['resume'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', restheme, nodestr)

		n1.resume = 'skip'
		restheme = copy(basetheme)
		restheme.update(Flowchart.THEMES['default']['skip'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', restheme, nodestr)

		n1.resume = 'skip+'
		restheme = copy(basetheme)
		restheme.update(Flowchart.THEMES['default']['skip+'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', restheme, nodestr)

	@unittest.skipIf(not which('dot'), 'Graphviz not installed.')
	def testGenerate(self):
		tmpdir  = tempfile.gettempdir()
		fcfile  = path.join(tmpdir, 'testGenerate.svg')
		dotfile = path.join(tmpdir, 'testGenerate.dot')
		fc = Flowchart(fcfile = fcfile, dotfile = dotfile)
		n1 = Node('n1')
		n2 = Node('n2', aggr = 'g1', exdir = '/a/b/')
		n3 = Node('n3', aggr = 'g1', resume = 'resume')
		fc.addNode(n1)
		fc.addNode(n2, 'start')
		fc.addNode(n3, 'end')
		fc.addLink(n1, n2)
		fc.addLink(n2, n3)

		n1theme = copy(Flowchart.THEMES['default']['base'])
		n2theme = copy(Flowchart.THEMES['default']['base'])
		n3theme = copy(Flowchart.THEMES['default']['base'])
		n2theme.update(Flowchart.THEMES['default']['start'])
		n2theme.update(Flowchart.THEMES['default']['export'])
		n3theme.update(Flowchart.THEMES['default']['end'])
		n3theme.update(Flowchart.THEMES['default']['resume'])
		nodestr = fc._dotnodes()
		self.assertInDot('n1', n1theme, nodestr)
		self.assertInDot('n2', n2theme, nodestr)
		self.assertInDot('n3', n3theme, nodestr)
		self.assertEqual(fc._dotlinks(), ['    "n1" -> "n2"', '    "n2" -> "n3"'])
		self.assertEqual(fc._dotgroups(), [
			'    subgraph cluster_g1 {',
			'        label = "g1";',
			'        color = "#eeeeee";',
			'        style = "filled";',
			'        "n2";',
			'        "n3";',
			'    }'
		])
		fc.generate()
		self.assertTrue(path.exists(fcfile))
		self.assertTrue(path.exists(dotfile))
		with open(dotfile) as f:
			self.assertEqual(f.read().splitlines(), """digraph PyPPL {
    "n1" [color="#000000" fillcolor="#ffffff" fontcolor="#000000" shape="box" style="rounded,filled"]
    "n2" [color="#259229" fillcolor="#ffffff" fontcolor="#c71be4" shape="box" style="filled"]
    "n3" [color="#d63125" fillcolor="#b9ffcd" fontcolor="#000000" shape="box" style="filled"]
    "n1" -> "n2"
    "n2" -> "n3"
    subgraph cluster_g1 {
        label = "g1";
        color = "#eeeeee";
        style = "filled";
        "n2";
        "n3";
    }
}
""".splitlines())

	@unittest.skipIf(not which('dot'), 'Graphviz not installed.')
	def testDark(self):
		self.maxDiff = None
		tmpdir  = tempfile.gettempdir()
		fcfile  = path.join(tmpdir, 'testDark.svg')
		dotfile = path.join(tmpdir, 'testDark.dot')
		fc = Flowchart(fcfile = fcfile, dotfile = dotfile)
		fc.setTheme('dark')
		n1 = Node('n1')
		n2 = Node('n2', aggr = 'g1', exdir = '/a/b/')
		n3 = Node('n3', aggr = 'g1', resume = 'resume')
		fc.addNode(n1)
		fc.addNode(n2, 'start')
		fc.addNode(n3, 'end')
		fc.addLink(n1, n2)
		fc.addLink(n2, n3)

		n1theme = copy(Flowchart.THEMES['dark']['base'])
		n2theme = copy(Flowchart.THEMES['dark']['base'])
		n3theme = copy(Flowchart.THEMES['dark']['base'])
		n2theme.update(Flowchart.THEMES['dark']['start'])
		n2theme.update(Flowchart.THEMES['dark']['export'])
		n3theme.update(Flowchart.THEMES['dark']['end'])
		n3theme.update(Flowchart.THEMES['dark']['resume'])
		nodestr = fc._dotnodes()

		self.assertInDot('n1', n1theme, nodestr)
		self.assertInDot('n2', n2theme, nodestr)
		self.assertInDot('n3', n3theme, nodestr)
		self.assertEqual(fc._dotlinks(), ['    "n1" -> "n2"', '    "n2" -> "n3"'])
		self.assertEqual(fc._dotgroups(), [
			'    subgraph cluster_g1 {',
			'        label = "g1";',
			'        color = "#eeeeee";',
			'        style = "filled";',
			'        "n2";',
			'        "n3";',
			'    }'
		])
		fc.generate()
		self.assertTrue(path.exists(fcfile))
		self.assertTrue(path.exists(dotfile))
		with open(dotfile) as f:
			self.assertEqual(f.read().splitlines(), """digraph PyPPL {
    "n1" [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape="box" style="rounded,filled"]
    "n2" [color="#59b95d" fillcolor="#555555" fontcolor="#db95e6" penwidth="2" shape="box" style="filled"]
    "n3" [color="#ea7d75" fillcolor="#1b5a2d" fontcolor="#ffffff" penwidth="2" shape="box" style="filled"]
    "n1" -> "n2"
    "n2" -> "n3"
    subgraph cluster_g1 {
        label = "g1";
        color = "#eeeeee";
        style = "filled";
        "n2";
        "n3";
    }
}
""".splitlines())

if __name__ == '__main__':
	unittest.main(verbosity=2)