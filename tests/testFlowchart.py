import testly, sys, helpers

if helpers.moduleInstalled('graphviz'):
	from os import path, makedirs
	from shutil import rmtree
	from tempfile import gettempdir
	from pyppl import Proc
	from pyppl.flowchart import Flowchart
	from graphviz import Digraph

	class TestFlowchart (testly.TestCase):

		def setUpMeta(self):
			self.testdir = path.join(gettempdir(), 'PyPPL_unittest', 'TestFlowchart')
			if path.exists(self.testdir):
				rmtree(self.testdir)
			makedirs(self.testdir)

		def dataProvider_testInit(self):
			dotfile = path.join(self.testdir, 'test.dot')
			svgfile = path.join(self.testdir, 'test.svg')
			yield dotfile, svgfile
			yield 'x', 'y'
			yield 'x', svgfile
			yield dotfile, 'y'

		def testInit(self, fcfile, dotfile):
			fc = Flowchart(fcfile, dotfile)
			self.assertEqual(fc.fcfile, fcfile)
			self.assertEqual(fc.dotfile, dotfile)
			self.assertIsInstance(fc, Flowchart)
			self.assertIsInstance(fc.graph, Digraph)
			self.assertDictEqual(fc.theme, Flowchart.THEMES['default'])
			self.assertDictEqual(fc.nodes, {})
			self.assertListEqual(fc.starts, [])
			self.assertListEqual(fc.ends, [])
			self.assertListEqual(fc.links, [])

		def dataProvider_testSetTheme(self):
			yield 'default', 'default', Flowchart.THEMES['default']
			yield 'dark', 'default', Flowchart.THEMES['dark']
			yield {}, 'default', {
				'aggr': {'color': '#eeeeee', 'style': 'filled'},
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
			}
			yield {'base': {'shape': 'circle'}}, 'dark', {
				'aggr': {'color': '#eeeeee', 'style': 'filled'},
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
			}

		def testSetTheme(self, theme, tmbase, tmout):
			self.maxDiff = None
			dotfile = path.join(self.testdir, 'test.dot')
			fcfile = path.join(self.testdir, 'test.svg')
			fc = Flowchart(dotfile, fcfile)
			fc.setTheme(theme, tmbase)
			self.assertDictEqual(fc.theme, tmout)

		def dataProvider_testAddNode(self):
			p1 = Proc()
			p2 = Proc()
			p3 = Proc()
			p4 = Proc()
			p5 = Proc()
			p6 = Proc()
			p4.aggr = 'aggr1'
			p5.aggr = 'aggr1'
			p6.aggr = 'aggr2'

			yield p1, 'start', True, False, Flowchart.ROOTGROUP
			yield p2, 'end', False, True, Flowchart.ROOTGROUP
			yield p3, None, False, False, Flowchart.ROOTGROUP
			yield p4, None, False, False, 'aggr1'
			yield p5, 'start', True, False, 'aggr1'
			yield p6, 'end', False, True, 'aggr2'

		def testAddNode(self, proc, role, instarts, inends, group):
			dotfile = path.join(self.testdir, 'test.dot')
			fcfile  = path.join(self.testdir, 'test.svg')
			fc = Flowchart(fcfile, dotfile)
			fc.addNode(proc, role)
			self.assertEqual(proc in fc.starts, instarts)
			self.assertEqual(proc in fc.ends, inends)
			self.assertTrue(proc in fc.nodes[group])

		def dataProvider_testAddLink(self):
			p1 = Proc()
			p2 = Proc()
			p3 = Proc()
			p4 = Proc()
			p5 = Proc()
			p6 = Proc()
			yield p1, p2
			yield p1, p3
			yield p4, p3
			yield p5, p4
			yield p5, p6

		def testAddLink(self, n1, n2):
			dotfile = path.join(self.testdir, 'test.dot')
			fcfile  = path.join(self.testdir, 'test.svg')
			fc = Flowchart(fcfile, dotfile)
			fc.addLink(n1, n2)
			self.assertIn((n1, n2), fc.links)

		def dataProvider_testAssemble(self):
			p1 = Proc(tag = '1st')
			p2 = Proc(desc = 'The description of p2')
			p3 = Proc()
			p4 = Proc()
			p5 = Proc()
			p6 = Proc()
			p4.aggr = 'aggr1'
			p5.aggr = 'aggr1'
			p6.aggr = 'aggr2'
			p5.resume = 'skip+'
			p6.exdir  = '.'

			yield [p1, p2, p3, p4], [p1], [p4], [(p1, p2), (p2, p3), (p3, p4)], 'default', 'default', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#259229" fillcolor="#ffffff" fontcolor="#000000" shape=box style=filled]',
				'\tp2 [color="#000000" fillcolor="#ffffff" fontcolor="#000000" shape=box style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#000000" fillcolor="#ffffff" fontcolor="#000000" shape=box style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#d63125" fillcolor="#ffffff" fontcolor="#000000" shape=box style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'}'
			])

			yield [p1, p2, p3, p4], [p1], [p4], [(p1, p2), (p2, p3), (p3, p4)], 'dark', 'default', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#59b95d" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=box style=filled]',
				'\tp2 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=box style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=box style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#ea7d75" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=box style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'}'
			])

			yield [p1, p2, p3, p4, p5, p6], [p1, p5], [p4, p5], [(p1, p2), (p2, p3), (p3, p4), (p2, p5), (p3, p5), (p5, p6)], {'base': {'shape': 'circle'}}, 'dark', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#59b95d" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\tp2 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=circle style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=circle style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#ea7d75" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\t\tp5 [color="#ea7d75" fillcolor="#d1cfcf" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\tsubgraph cluster_aggr2 {',
				'\t\tp6 [color="#ffffff" fillcolor="#555555" fontcolor="#db95e6" shape=circle style="rounded,filled"]',
				'\t\tcolor="#eeeeee" label=aggr2 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'\tp2 -> p5',
				'\tp3 -> p5',
				'\tp5 -> p6',
				'}'
			])

		def testAssemble(self, nodes, starts, ends, links, theme, basetheme, src):
			self.maxDiff = None
			dotfile = path.join(self.testdir, 'test.dot')
			fcfile  = path.join(self.testdir, 'test.svg')
			fc = Flowchart(fcfile, dotfile)
			fc.setTheme(theme, basetheme)
			for node in nodes:
				if node in starts:
					fc.addNode(node, 'start')
				if node in ends:
					fc.addNode(node, 'end')
				fc.addNode(node)
			for link in links:
				fc.addLink(*link)
			fc._assemble()
			helpers.assertTextEqual(self, fc.graph.source, src)

		def dataProvider_testGenerate(self):
			p1 = Proc(tag = '1st')
			p2 = Proc(desc = 'The description of p2')
			p3 = Proc()
			p4 = Proc()
			p5 = Proc()
			p6 = Proc()
			p4.aggr = 'aggr1'
			p5.aggr = 'aggr1'
			p6.aggr = 'aggr2'
			p5.resume = 'skip+'

			dotfile1 = path.join(self.testdir, 'dotfile1.txt')
			svgfile1 = path.join(self.testdir, 'svgfile1.svg')
			yield dotfile1, svgfile1, [p1, p2, p3, p4], [p1], [p4], [(p1, p2), (p2, p3), (p3, p4)], 'default', 'default', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#259229" fillcolor="#ffffff" fontcolor="#000000" shape=box style=filled]',
				'\tp2 [color="#000000" fillcolor="#ffffff" fontcolor="#000000" shape=box style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#000000" fillcolor="#ffffff" fontcolor="#000000" shape=box style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#d63125" fillcolor="#ffffff" fontcolor="#000000" shape=box style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'}',
				'',
			]), [
				'<svg width="94pt" height="281pt"',
				' viewBox="0.00 0.00 94.00 280.80" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
				'<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 276.8)">',
				'<title>PyPPL</title>',
				'<polygon fill="white" stroke="none" points="-4,4 -4,-276.8 90,-276.8 90,4 -4,4"/>',
				'<g id="clust1" class="cluster"><title>cluster_aggr1</title>',
				'<polygon fill="#eeeeee" stroke="#eeeeee" points="8,-8 8,-84.8 78,-84.8 78,-8 8,-8"/>',
				'<text text-anchor="middle" x="43" y="-68.2" font-family="Times,serif" font-size="14.00">aggr1</text>',
				'</g>',
				'<!-- p1.1st -->',
				'<g id="node1" class="node"><title>p1.1st</title>',
				'<polygon fill="#ffffff" stroke="#259229" points="70,-272.8 16,-272.8 16,-236.8 70,-236.8 70,-272.8"/>',
				'<text text-anchor="middle" x="43" y="-250.6" font-family="Times,serif" font-size="14.00" fill="#000000">p1.1st</text>',
				'</g>',
				'<!-- p2 -->',
				'<g id="node2" class="node"><title>p2</title>',
				'<g id="a_node2"><a xlink:title="The description of p2">',
				'<path fill="#ffffff" stroke="#000000" d="M58,-200.8C58,-200.8 28,-200.8 28,-200.8 22,-200.8 16,-194.8 16,-188.8 16,-188.8 16,-176.8 16,-176.8 16,-170.8 22,-164.8 28,-164.8 28,-164.8 58,-164.8 58,-164.8 64,-164.8 70,-170.8 70,-176.8 70,-176.8 70,-188.8 70,-188.8 70,-194.8 64,-200.8 58,-200.8"/>',
				'<text text-anchor="middle" x="43" y="-178.6" font-family="Times,serif" font-size="14.00" fill="#000000">p2</text>',
				'</a>',
				'</g>',
				'</g>',
				'<!-- p1.1st&#45;&gt;p2 -->',
				'<g id="edge1" class="edge"><title>p1.1st&#45;&gt;p2</title>',
				'<path fill="none" stroke="black" d="M43,-236.497C43,-228.783 43,-219.512 43,-210.912"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-210.904 43,-200.904 39.5001,-210.904 46.5001,-210.904"/>',
				'</g>',
				'<!-- p3 -->',
				'<g id="node3" class="node"><title>p3</title>',
				'<path fill="#ffffff" stroke="#000000" d="M58,-128.8C58,-128.8 28,-128.8 28,-128.8 22,-128.8 16,-122.8 16,-116.8 16,-116.8 16,-104.8 16,-104.8 16,-98.8 22,-92.8 28,-92.8 28,-92.8 58,-92.8 58,-92.8 64,-92.8 70,-98.8 70,-104.8 70,-104.8 70,-116.8 70,-116.8 70,-122.8 64,-128.8 58,-128.8"/>',
				'<text text-anchor="middle" x="43" y="-106.6" font-family="Times,serif" font-size="14.00" fill="#000000">p3</text>',
				'</g>',
				'<!-- p2&#45;&gt;p3 -->',
				'<g id="edge2" class="edge"><title>p2&#45;&gt;p3</title>',
				'<path fill="none" stroke="black" d="M43,-164.497C43,-156.783 43,-147.512 43,-138.912"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-138.904 43,-128.904 39.5001,-138.904 46.5001,-138.904"/>',
				'</g>',
				'<!-- p4 -->',
				'<g id="node4" class="node"><title>p4</title>',
				'<polygon fill="#ffffff" stroke="#d63125" points="70,-52 16,-52 16,-16 70,-16 70,-52"/>',
				'<text text-anchor="middle" x="43" y="-29.8" font-family="Times,serif" font-size="14.00" fill="#000000">p4</text>',
				'</g>',
				'<!-- p3&#45;&gt;p4 -->',
				'<g id="edge3" class="edge"><title>p3&#45;&gt;p4</title>',
				'<path fill="none" stroke="black" d="M43,-92.4514C43,-83.5771 43,-72.5644 43,-62.5623"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-62.2545 43,-52.2546 39.5001,-62.2546 46.5001,-62.2545"/>',
				'</g>',
				'</g>',
				'</svg>',
			]

			dotfile2 = path.join(self.testdir, 'dotfile2.txt')
			svgfile2 = path.join(self.testdir, 'svgfile2.svg')
			yield dotfile2, svgfile2, [p1, p2, p3, p4], [p1], [p4], [(p1, p2), (p2, p3), (p3, p4)], 'dark', 'default', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#59b95d" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=box style=filled]',
				'\tp2 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=box style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=box style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#ea7d75" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=box style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'}',
				'',
			]), [
				'<svg width="94pt" height="281pt"',
				' viewBox="0.00 0.00 94.00 280.80" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
				'<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 276.8)">',
				'<title>PyPPL</title>',
				'<polygon fill="white" stroke="none" points="-4,4 -4,-276.8 90,-276.8 90,4 -4,4"/>',
				'<g id="clust1" class="cluster"><title>cluster_aggr1</title>',
				'<polygon fill="#eeeeee" stroke="#eeeeee" points="8,-8 8,-84.8 78,-84.8 78,-8 8,-8"/>',
				'<text text-anchor="middle" x="43" y="-68.2" font-family="Times,serif" font-size="14.00">aggr1</text>',
				'</g>',
				'<!-- p1.1st -->',
				'<g id="node1" class="node"><title>p1.1st</title>',
				'<polygon fill="#555555" stroke="#59b95d" stroke-width="2" points="70,-272.8 16,-272.8 16,-236.8 70,-236.8 70,-272.8"/>',
				'<text text-anchor="middle" x="43" y="-250.6" font-family="Times,serif" font-size="14.00" fill="#ffffff">p1.1st</text>',
				'</g>',
				'<!-- p2 -->',
				'<g id="node2" class="node"><title>p2</title>',
				'<g id="a_node2"><a xlink:title="The description of p2">',
				'<path fill="#555555" stroke="#ffffff" d="M58,-200.8C58,-200.8 28,-200.8 28,-200.8 22,-200.8 16,-194.8 16,-188.8 16,-188.8 16,-176.8 16,-176.8 16,-170.8 22,-164.8 28,-164.8 28,-164.8 58,-164.8 58,-164.8 64,-164.8 70,-170.8 70,-176.8 70,-176.8 70,-188.8 70,-188.8 70,-194.8 64,-200.8 58,-200.8"/>',
				'<text text-anchor="middle" x="43" y="-178.6" font-family="Times,serif" font-size="14.00" fill="#ffffff">p2</text>',
				'</a>',
				'</g>',
				'</g>',
				'<!-- p1.1st&#45;&gt;p2 -->',
				'<g id="edge1" class="edge"><title>p1.1st&#45;&gt;p2</title>',
				'<path fill="none" stroke="black" d="M43,-236.497C43,-228.783 43,-219.512 43,-210.912"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-210.904 43,-200.904 39.5001,-210.904 46.5001,-210.904"/>',
				'</g>',
				'<!-- p3 -->',
				'<g id="node3" class="node"><title>p3</title>',
				'<path fill="#555555" stroke="#ffffff" d="M58,-128.8C58,-128.8 28,-128.8 28,-128.8 22,-128.8 16,-122.8 16,-116.8 16,-116.8 16,-104.8 16,-104.8 16,-98.8 22,-92.8 28,-92.8 28,-92.8 58,-92.8 58,-92.8 64,-92.8 70,-98.8 70,-104.8 70,-104.8 70,-116.8 70,-116.8 70,-122.8 64,-128.8 58,-128.8"/>',
				'<text text-anchor="middle" x="43" y="-106.6" font-family="Times,serif" font-size="14.00" fill="#ffffff">p3</text>',
				'</g>',
				'<!-- p2&#45;&gt;p3 -->',
				'<g id="edge2" class="edge"><title>p2&#45;&gt;p3</title>',
				'<path fill="none" stroke="black" d="M43,-164.497C43,-156.783 43,-147.512 43,-138.912"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-138.904 43,-128.904 39.5001,-138.904 46.5001,-138.904"/>',
				'</g>',
				'<!-- p4 -->',
				'<g id="node4" class="node"><title>p4</title>',
				'<polygon fill="#555555" stroke="#ea7d75" stroke-width="2" points="70,-52 16,-52 16,-16 70,-16 70,-52"/>',
				'<text text-anchor="middle" x="43" y="-29.8" font-family="Times,serif" font-size="14.00" fill="#ffffff">p4</text>',
				'</g>',
				'<!-- p3&#45;&gt;p4 -->',
				'<g id="edge3" class="edge"><title>p3&#45;&gt;p4</title>',
				'<path fill="none" stroke="black" d="M43,-92.4514C43,-83.5771 43,-72.5644 43,-62.5623"/>',
				'<polygon fill="black" stroke="black" points="46.5001,-62.2545 43,-52.2546 39.5001,-62.2546 46.5001,-62.2545"/>',
				'</g>',
				'</g>',
				'</svg>',
			]

			dotfile3 = path.join(self.testdir, 'dotfile3.txt')
			svgfile3 = path.join(self.testdir, 'svgfile3.svg')
			yield dotfile3, svgfile3, [p1, p2, p3, p4, p5, p6], [p1, p5], [p4, p5], [(p1, p2), (p2, p3), (p3, p4), (p2, p5), (p3, p5), (p5, p6)], {'base': {'shape': 'circle'}}, 'dark', '\n'.join([
				'digraph PyPPL {',
				'\t"p1.1st" [color="#59b95d" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\tp2 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=circle style="rounded,filled" tooltip="The description of p2"]',
				'\tp3 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=circle style="rounded,filled"]',
				'\tsubgraph cluster_aggr1 {',
				'\t\tp4 [color="#ea7d75" fillcolor="#555555" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\t\tp5 [color="#ea7d75" fillcolor="#d1cfcf" fontcolor="#ffffff" penwidth=2 shape=circle style=filled]',
				'\t\tcolor="#eeeeee" label=aggr1 style=filled',
				'\t}',
				'\tsubgraph cluster_aggr2 {',
				'\t\tp6 [color="#ffffff" fillcolor="#555555" fontcolor="#ffffff" shape=circle style="rounded,filled"]',
				'\t\tcolor="#eeeeee" label=aggr2 style=filled',
				'\t}',
				'\t"p1.1st" -> p2',
				'\tp2 -> p3',
				'\tp3 -> p4',
				'\tp2 -> p5',
				'\tp3 -> p5',
				'\tp5 -> p6',
				'}',
				'',
			]), [
				'<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 415.898)">',
				'<title>PyPPL</title>',
				'<polygon fill="white" stroke="none" points="-4,4 -4,-415.898 137,-415.898 137,4 -4,4"/>',
				'<g id="clust1" class="cluster"><title>cluster_aggr1</title>',
				'<polygon fill="#eeeeee" stroke="#eeeeee" points="8,-98.1869 8,-180.374 125,-180.374 125,-98.1869 8,-98.1869"/>',
				'<text text-anchor="middle" x="66.5" y="-163.774" font-family="Times,serif" font-size="14.00">aggr1</text>',
				'</g>',
				'<g id="clust2" class="cluster"><title>cluster_aggr2</title>',
				'<polygon fill="#eeeeee" stroke="#eeeeee" points="67,-8 67,-90.1869 125,-90.1869 125,-8 67,-8"/>',
				'<text text-anchor="middle" x="96" y="-73.5869" font-family="Times,serif" font-size="14.00">aggr2</text>',
				'</g>',
				'<!-- p1.1st -->',
				'<g id="node1" class="node"><title>p1.1st</title>',
				'<ellipse fill="#555555" stroke="#59b95d" stroke-width="2" cx="71" cy="-377.523" rx="34.2513" ry="34.2513"/>',
				'<text text-anchor="middle" x="71" y="-373.323" font-family="Times,serif" font-size="14.00" fill="#ffffff">p1.1st</text>',
				'</g>',
				'<!-- p2 -->',
				'<g id="node2" class="node"><title>p2</title>',
				'<g id="a_node2"><a xlink:title="The description of p2">',
				'<ellipse fill="#555555" stroke="#ffffff" cx="71" cy="-286.454" rx="20.8887" ry="20.8887"/>',
				'<text text-anchor="middle" x="71" y="-282.254" font-family="Times,serif" font-size="14.00" fill="#ffffff">p2</text>',
				'</a>',
				'</g>',
				'</g>',
				'<!-- p1.1st&#45;&gt;p2 -->',
				'<g id="edge1" class="edge"><title>p1.1st&#45;&gt;p2</title>',
				'<path fill="none" stroke="black" d="M71,-343.104C71,-334.729 71,-325.794 71,-317.59"/>',
				'<polygon fill="black" stroke="black" points="74.5001,-317.334 71,-307.334 67.5001,-317.334 74.5001,-317.334"/>',
				'</g>',
				'<!-- p3 -->',
				'<g id="node3" class="node"><title>p3</title>',
				'<ellipse fill="#555555" stroke="#ffffff" cx="47" cy="-209.067" rx="20.8887" ry="20.8887"/>',
				'<text text-anchor="middle" x="47" y="-204.867" font-family="Times,serif" font-size="14.00" fill="#ffffff">p3</text>',
				'</g>',
				'<!-- p2&#45;&gt;p3 -->',
				'<g id="edge2" class="edge"><title>p2&#45;&gt;p3</title>',
				'<path fill="none" stroke="black" d="M64.9438,-266.431C62.272,-258.038 59.0742,-247.994 56.1231,-238.724"/>',
				'<polygon fill="black" stroke="black" points="59.423,-237.551 53.0543,-229.084 52.7528,-239.675 59.423,-237.551"/>',
				'</g>',
				'<!-- p5 -->',
				'<g id="node5" class="node"><title>p5</title>',
				'<ellipse fill="#d1cfcf" stroke="#ea7d75" stroke-width="2" cx="96" cy="-126.88" rx="20.8887" ry="20.8887"/>',
				'<text text-anchor="middle" x="96" y="-122.68" font-family="Times,serif" font-size="14.00" fill="#ffffff">p5</text>',
				'</g>',
				'<!-- p2&#45;&gt;p5 -->',
				'<g id="edge4" class="edge"><title>p2&#45;&gt;p5</title>',
				'<path fill="none" stroke="black" d="M74.1157,-265.816C78.4198,-238.687 86.2221,-189.51 91.2539,-157.795"/>',
				'<polygon fill="black" stroke="black" points="94.7347,-158.191 92.845,-147.766 87.8212,-157.094 94.7347,-158.191"/>',
				'</g>',
				'<!-- p4 -->',
				'<g id="node4" class="node"><title>p4</title>',
				'<ellipse fill="#555555" stroke="#ea7d75" stroke-width="2" cx="37" cy="-126.88" rx="20.8887" ry="20.8887"/>',
				'<text text-anchor="middle" x="37" y="-122.68" font-family="Times,serif" font-size="14.00" fill="#ffffff">p4</text>',
				'</g>',
				'<!-- p3&#45;&gt;p4 -->',
				'<g id="edge3" class="edge"><title>p3&#45;&gt;p4</title>',
				'<path fill="none" stroke="black" d="M44.5281,-188.246C43.3777,-179.021 41.9849,-167.853 40.7118,-157.644"/>',
				'<polygon fill="black" stroke="black" points="44.1542,-156.964 39.4435,-147.474 37.208,-157.83 44.1542,-156.964"/>',
				'</g>',
				'<!-- p3&#45;&gt;p5 -->',
				'<g id="edge5" class="edge"><title>p3&#45;&gt;p5</title>',
				'<path fill="none" stroke="black" d="M58.9686,-192.186C61.6985,-188.378 64.5229,-184.281 67,-180.374 72.1851,-172.196 77.4302,-163.032 82.0073,-154.678"/>',
				'<polygon fill="black" stroke="black" points="85.1903,-156.149 86.8524,-145.686 79.0278,-152.829 85.1903,-156.149"/>',
				'</g>',
				'<!-- p6 -->',
				'<g id="node6" class="node"><title>p6</title>',
				'<ellipse fill="#555555" stroke="#ffffff" cx="96" cy="-36.6935" rx="20.8887" ry="20.8887"/>',
				'<text text-anchor="middle" x="96" y="-32.4935" font-family="Times,serif" font-size="14.00" fill="#ffffff">p6</text>',
				'</g>',
				'<!-- p5&#45;&gt;p6 -->',
				'<g id="edge6" class="edge"><title>p5&#45;&gt;p6</title>',
				'<path fill="none" stroke="black" d="M96,-105.869C96,-94.5941 96,-80.2882 96,-67.6958"/>',
				'<polygon fill="black" stroke="black" points="99.5001,-67.6252 96,-57.6252 92.5001,-67.6253 99.5001,-67.6252"/>',
				'</g>',
				'</g>',
				'</svg>',
			]

		def testGenerate(self, dotfile, fcfile, nodes, starts, ends, links, theme, basetheme, src, svg):
			self.maxDiff = None
			fc = Flowchart(dotfile = dotfile, fcfile = fcfile)
			fc.setTheme(theme, basetheme)
			for node in nodes:
				if node in starts:
					fc.addNode(node, 'start')
				if node in ends:
					fc.addNode(node, 'end')
				fc.addNode(node)
			for link in links:
				fc.addLink(*link)
			fc.generate()
			with open(fc.dotfile) as f:
				helpers.assertTextEqual(self, f.read(), src)
			helpers.assertInSvgFile(self, svg, fc.fcfile, '<g id="n')


if __name__ == '__main__':
	if helpers.moduleInstalled('graphviz'):
		testly.main(verbosity=2)
	else:
		sys.stderr.write('Test skipped, graphviz not installed\n')