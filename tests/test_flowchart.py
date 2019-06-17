import pytest

try:
	from graphviz import Digraph
except ImportError:
	pytest.skip('graphviz is not installed', allow_module_level=True)

from pyppl.flowchart import Flowchart, THEMES, ROOTGROUP

pytest_plugins = ["tests.fixt_flowchart"]

class TestFlowchart:
	@classmethod
	def setup_class(cls):
		cls.fc = Flowchart('', '')

	def test_init(self, tmpdir):
		self.dotfile = str(tmpdir / 'flowchart.dot')
		self.fcfile = str(tmpdir / 'flowchart.svg')
		assert isinstance(self.fc, Flowchart)
		assert isinstance(self.fc.graph, Digraph)
		assert self.fc.theme == THEMES['default']
		assert self.fc.nodes == {}
		assert self.fc.starts == []
		assert self.fc.ends == []
		assert self.fc.links == []

	@pytest.mark.parametrize('theme, tmbase, tmout', [
		('default', 'default', THEMES['default']),
		('dark', 'default', THEMES['dark']),
		({}, 'default', {
			'procset': {'color': '#eeeeee', 'style': 'filled'},
			'base': {'color': '#000000',
					'fillcolor': '#ffffff',
					'fontcolor': '#000000',
					'shape': 'box',
					'style': 'rounded,filled'},
			'end': {'color': '#d63125', 'style': 'filled'},
			'export': {'fontcolor': '#c71be4'},
			'resume': {'fillcolor': '#b9ffcd'},
			'resume+': {'fillcolor': '#58b773'},
			'skip': {'fillcolor': '#eaeaea'},
			'skip+': {'fillcolor': '#b5b3b3'},
			'start': {'color': '#259229', 'style': 'filled'}
		}),
		({'base': {'shape': 'circle'}}, 'dark', {
			'procset': {'color': '#eeeeee', 'style': 'filled'},
			'base': {'color': '#ffffff',
					'fillcolor': '#555555',
					'fontcolor': '#ffffff',
					'shape': 'circle',
					'style': 'rounded,filled'},
			'end': {'color': '#ea7d75', 'penwidth': 2, 'style': 'filled'},
			'export': {'fontcolor': '#db95e6'},
			'resume': {'fillcolor': '#1b5a2d'},
			'resume+': {'fillcolor': '#a7f2bb'},
			'skip': {'fillcolor': '#b5b3b3'},
			'skip+': {'fillcolor': '#d1cfcf'},
			'start': {'color': '#59b95d', 'penwidth': 2, 'style': 'filled'}
		})
	])
	def test_settheme(self, theme, tmbase, tmout):
		self.fc.setTheme(theme, tmbase)
		assert self.fc.theme == tmout

	@pytest.mark.parametrize('proc, role, instarts, inends, group', [
		('p1', 'start', True, False, ROOTGROUP),
		('p2', 'end', False, True, ROOTGROUP),
		('p3', None, False, False, ROOTGROUP),
		('p_procset1', None, False, False, 'procset1'),
		('p_procset1', 'start', True, False, 'procset1'),
		('p_procset2', 'end', False, True, 'procset2'),
	])
	def test_addNode(self, procs, proc, role, instarts, inends, group):
		proc = procs[proc]
		self.fc.addNode(proc, role)
		assert (proc in self.fc.starts) == instarts
		assert (proc in self.fc.ends) == inends
		assert proc in self.fc.nodes[group]

	@pytest.mark.parametrize('n1, n2', [
		('p1', 'p2')
	])
	def test_addLink(self, procs, n1, n2):
		n1 = procs[n1]
		n2 = procs[n2]
		self.fc.addLink(n1, n2)
		assert (n1, n2) in self.fc.links

	@pytest.mark.parametrize('nodes, starts, ends, links, theme, basetheme, srcs, svgs', [
		(['p_tag_1st', 'p_desc', 'p1', 'p_procset1'],
		 ['p_tag_1st'],
		 ['p_procset1'],
		 [('p_tag_1st', 'p_desc'), ('p_desc', 'p1'), ('p1', 'p_procset1')],
		 'default', 'default',
		 ['digraph PyPPL {',
		  'p_tag_1st.1st', 'color="#259229"',
		  'p_desc', 'color="#000000"',
		  'p1', 'color="#000000"',
		  'subgraph cluster_procset1 {',
		  'p_procset1', 'color="#d63125"',
		  'color="#eeeeee"',
		  '"p_tag_1st.1st" -> p_desc',
		  'p_desc -> p1',
		  'p1 -> p_procset1'],
		 ['<title>PyPPL</title>',
		  '<title>cluster_procset1</title>',
		  '<!-- p_tag_1st.1st -->',
		  '<title>p_tag_1st.1st</title>',
		  '<!-- p_desc -->',
		  '<title>p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p1 -->',
		  '<title>p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_procset1 -->',
		  '<title>p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>',]),

		(['p_tag_1st', 'p_desc', 'p1', 'p_procset1'],
		 ['p_tag_1st'],
		 ['p_procset1'],
		 [('p_tag_1st', 'p_desc'), ('p_desc', 'p1'), ('p1', 'p_procset1')],
		 'dark', 'default',
		 ['digraph PyPPL {',
		  'p_tag_1st.1st', 'color="#59b95d"',
		  'p_desc', 'color="#ffffff"',
		  'p1', 'color="#ffffff"',
		  'subgraph cluster_procset1 {',
		  'p_procset1', 'color="#ea7d75"',
		  'color="#eeeeee"',
		  '"p_tag_1st.1st" -> p_desc',
		  'p_desc -> p1',
		  'p1 -> p_procset1'],
		 ['<title>PyPPL</title>',
		  '<title>cluster_procset1</title>',
		  '<!-- p_tag_1st.1st -->',
		  '<title>p_tag_1st.1st</title>',
		  '<!-- p_desc -->',
		  '<title>p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p1 -->',
		  '<title>p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_procset1 -->',
		  '<title>p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>']),
		#  p1           p2        p3    p4            p5                     p6
		(['p_tag_1st', 'p_desc', 'p1', 'p_procset1', 'p_procset1_skipplus', 'p_procset2_exdir'],
		 ['p_tag_1st', 'p_procset1_skipplus'],
		 ['p_procset1', 'p_procset1'],
		 [('p_tag_1st', 'p_desc'),
		  ('p_desc', 'p1'),
		  ('p1', 'p_procset1'),
		  ('p_desc', 'p_procset1_skipplus'),
		  ('p1', 'p_procset1_skipplus'),
		  ('p_procset1_skipplus', 'p_procset2_exdir')],
		 {'base': {'shape': 'circle'}}, 'dark',
		 ['digraph PyPPL {',
		  'p_tag_1st.1st', 'color="#59b95d"',
		  'p_desc', 'color="#ffffff"',
		  'p1', 'color="#ffffff"',
		  'subgraph cluster_procset1 {',
		  'p_procset1', 'color="#ea7d75"',
		  'p_procset1_skipplus', 'color="#59b95d"',
		  'color="#eeeeee"',
		  'subgraph cluster_procset2 {',
		  'p_procset2_exdir', 'color="#ffffff"',
		  'color="#eeeeee"',
		  '"p_tag_1st.1st" -> p_desc',
		  'p_desc -> p1',
		  'p1 -> p_procset1',
		  'p_desc -> p_procset1_skipplus',
		  'p1 -> p_procset1_skipplus',
		  'p_procset1_skipplus -> p_procset2_exdir'],
		 ['<title>PyPPL</title>',
		  '<title>cluster_procset1</title>',
		  '<title>cluster_procset2</title>',
		  '<!-- p_tag_1st.1st -->',
		  '<title>p_tag_1st.1st</title>',
		  '<!-- p_desc -->',
		  '<title>p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p_tag_1st.1st&#45;&gt;p_desc -->',
		  '<title>p_tag_1st.1st&#45;&gt;p_desc</title>',
		  '<!-- p1 -->',
		  '<title>p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_desc&#45;&gt;p1 -->',
		  '<title>p_desc&#45;&gt;p1</title>',
		  '<!-- p_procset1_skipplus -->',
		  '<title>p_procset1_skipplus</title>',
		  '<!-- p_desc&#45;&gt;p_procset1_skipplus -->',
		  '<title>p_desc&#45;&gt;p_procset1_skipplus</title>',
		  '<!-- p_desc&#45;&gt;p_procset1_skipplus -->',
		  '<title>p_desc&#45;&gt;p_procset1_skipplus</title>',
		  '<!-- p_procset1 -->',
		  '<title>p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1 -->',
		  '<title>p1&#45;&gt;p_procset1</title>',
		  '<!-- p1&#45;&gt;p_procset1_skipplus -->',
		  '<title>p1&#45;&gt;p_procset1_skipplus</title>',
		  '<!-- p1&#45;&gt;p_procset1_skipplus -->',
		  '<title>p1&#45;&gt;p_procset1_skipplus</title>',
		  '<!-- p_procset2_exdir -->',
		  '<title>p_procset2_exdir</title>',
		  '<!-- p_procset1_skipplus&#45;&gt;p_procset2_exdir -->',
		  '<title>p_procset1_skipplus&#45;&gt;p_procset2_exdir</title>',
		  '<!-- p_procset1_skipplus&#45;&gt;p_procset2_exdir -->',
		  '<title>p_procset1_skipplus&#45;&gt;p_procset2_exdir</title>',]),
	])
	def test_assemble_and_generate(self, tmpdir, procs, nodes, starts, ends, links, theme, basetheme, srcs, svgs):
		self.fc = Flowchart(str(tmpdir / 'flowchart.svg'), str(tmpdir / 'flowchart.doct'))
		self.fc.setTheme(theme, basetheme)
		starts = [procs[start] for start in starts]
		ends = [procs[end] for end in ends]
		for node in nodes:
			node = procs[node]
			self.fc.addNode(node, 'start' if node in starts else 'end' if node in ends else None)
		for link in links:
			self.fc.addLink(procs[link[0]], procs[link[1]])
		self.fc._assemble()
		source = self.fc.graph.source
		for src in srcs:
			assert src in source
			source = source[(source.find(src) + len(src)):]
		self.fc.generate()
		with open(self.fc.fcfile) as ffc:
			svgsource = ffc.read()
		for svg in svgs:
			assert svg in svgsource
			svgsource = svgsource[(svgsource.find(svg) + len(svg)):]
