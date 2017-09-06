import sys
import shlex
from os import path
from .templates import TemplatePyPPL
from . import utils

class Flowchart(object):
	"""
	Draw flowchart for pipelines
	"""

	THEMES = {
		'default': {
			'base':  {
				'shape':     'box',
				'style':     'rounded,filled',
				'fillcolor': '#ffffff',
				'color':     '#000000',
				'fontcolor': '#000000',
			},
			'start': {
				'style': 'filled',
				'color': '#259229',
			},
			'end': {
				'style': 'filled',
				'color': '#d63125',
			},
			'export': {
				'fontcolor': '#c71be4',
			},
			'skip': {
				'fillcolor': '#eaeaea',
			},
			'skip2': {
				'fillcolor': '#e9e9e9',
			},
			'resume': {
				'fillcolor': '#b9ffcd',
			},
			'aggr': {
				'style': 'filled',
				'color': '#eeeeee',
			}
		},

		'dark': {

		}
	}

	def __init__(self, fcfile = None, dotfile = None, dot = 'dot -Tsvg {{dotfile}} -o {{fcfile}}'):
		self.fcfile  = fcfile
		self.dotfile = dotfile
		if fcfile is None:
			self.fcfile = path.splitext(sys.argv[0])[0] + '.pyppl.svg'
		if dotfile is None:
			self.dotfile = path.splitext(sys.argv[0])[0] + '.pyppl.dot'

		t = TemplatePyPPL(dot)
		self.command = shlex.split(t.render({'fcfile': self.fcfile, 'dotfile': self.dotfile}))
		self.theme   = Flowchart.THEMES['default']
		self.nodes   = []
		self.starts  = []
		self.ends    = []
		self.links   = []
		self.groups  = {}

	def setTheme(self, theme):
		if isinstance(theme, dict):
			self.theme = theme
		else:
			self.theme = Flowchart.THEMES[theme]

	def addNode(self, node, role = None):
		if node not in self.nodes:
			self.nodes.append(node)
		if role == 'start' and node not in self.starts:
			self.starts.append(node)
		if role == 'end' and node not in self.ends:
			self.ends.append(node)
		if node.aggr:
			if node.aggr not in self.groups:
				self.groups[node.aggr] = []
			if node not in self.groups[node.aggr]:
				self.groups[node.aggr].append(node)

	def addLink(self, node1, node2):
		if [node1, node2] not in self.links:
			self.links.append((node1, node2))

	def _dotnodes(self):
		dotstr = []
		for node in self.nodes:
			theme  = self.theme['base']
			if node in self.starts:
				theme.update(self.theme['start'])
			if node in self.ends:
				theme.update(self.theme['end'])
			if node.exdir:
				theme.update(self.theme['export'])
			if node.resume == True:
				theme.update(self.theme['resume'])
			elif node.resume:
				theme.update(self.theme[node.resume])
			dotstr.append('    "%s" [%s]' % (node.name(False), ' '.join(['%s="%s"' % (k,theme[k]) for k in sorted(theme.keys())])))
		return dotstr

	def _dotlinks(self):
		dotstr = []
		for node1, node2 in self.links:
			dotstr.append('    "%s" -> "%s"' % (node1.name(False), node2.name(False)))
		return dotstr

	def _dotgroups(self):
		dotstr = []
		theme  = self.theme['aggr']
		for aggr, nodes in self.groups.items():
			dotstr.append('    subgraph cluster_%s {' % aggr)
			dotstr.append('        label = "%s";' % aggr)
			for key in sorted(theme.keys()):
				dotstr.append('        %s = "%s";' % (key, theme[key]))
			for node in nodes:
				dotstr.append('        "%s";' % node.name(False))
			dotstr.append('    }')
		return dotstr

	def generate(self):
		dotstr  = ['digraph PyPPL {']
		dotstr.extend(self._dotnodes())
		dotstr.extend(self._dotlinks())
		dotstr.extend(self._dotgroups())
		dotstr.append('}')

		with open(self.dotfile, 'w') as fout:
			fout.write('\n'.join(dotstr) + '\n')
		
		rc = utils.dumbPopen(self.command).wait()
		if rc != 0:
			raise ValueError('Failed to generate flowcart file: %s.' % self.command)



		