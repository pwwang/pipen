import sys
import shlex
from os import path
from .templates import TemplatePyPPL
from . import utils

class Flowchart(object):
	"""
	Draw flowchart for pipelines

	@static variables:
		`THEMES`: predefined themes
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
				'color': '#259229', # green
			},
			'end': {
				'style': 'filled',
				'color': '#d63125', # red
			},
			'export': {
				'fontcolor': '#c71be4', # purple
			},
			'skip': {
				'fillcolor': '#eaeaea', # gray
			},
			'skip+': {
				'fillcolor': '#b5b3b3', # gray
			},
			'resume': {
				'fillcolor': '#b9ffcd', # light green
			},
			'resume+': {
				'fillcolor': '#58b773', # green
			},
			'aggr': {
				'style': 'filled',
				'color': '#eeeeee', # almost white
			}
		},

		'dark': {
			'base':  {
				'shape':     'box',
				'style':     'rounded,filled',
				'fillcolor': '#555555',
				'color':     '#ffffff',
				'fontcolor': '#ffffff',
			},
			'start': {
				'style': 'filled',
				'color': '#59b95d', # green
				'penwidth': 2,
			},
			'end': {
				'style': 'filled',
				'color': '#ea7d75', # red
				'penwidth': 2,
			},
			'export': {
				'fontcolor': '#db95e6', # purple
			},
			'skip': {
				'fillcolor': '#b5b3b3', # gray
			},
			'skip+': {
				'fillcolor': '#d1cfcf', # gray
			},
			'resume': {
				'fillcolor': '#1b5a2d', # green
			},
			'resume+': {
				'fillcolor': '#a7f2bb', # light green
			},
			'aggr': {
				'style': 'filled',
				'color': '#eeeeee', # almost white
			}
		}
	}

	def __init__(self, fcfile = None, dotfile = None, dot = 'dot -Tsvg {{dotfile}} -o {{fcfile}}'):
		"""
		The constructor
		@params:
			`fcfile`: The flowchart file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.svg'`
			`dotfile`: The dot file. Default: `path.splitext(sys.argv[0])[0] + '.pyppl.dot'`
			`dot`: The dot command. Default: `'dot -Tsvg {{dotfile}} -o {{fcfile}}'`
		"""
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
		"""
		Set the theme to be used
		@params:
			`theme`: The theme, could be the key of Flowchart.THEMES or a dict of a theme definition.
		"""
		if isinstance(theme, dict):
			self.theme = theme
		else:
			self.theme = Flowchart.THEMES[theme]

	def addNode(self, node, role = None):
		"""
		Add a node to the chart
		@params:
			`node`: The node
			`role`: Is it a starting node, an ending node or None. Default: None.
		"""
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
		"""
		Add a link to the chart
		@params:
			`node1`: The first node.
			`node2`: The second node.
		"""
		if (node1, node2) not in self.links:
			self.links.append((node1, node2))

	def _dotnodes(self):
		"""
		Convert nodes to dot language.
		@returns:
			The string in dot language for all nodes.
		"""
		dotstr = []
		for node in self.nodes:
			theme  = {key:val for key,val in self.theme['base'].items()}
			if node in self.starts:
				theme.update(self.theme['start'])
			if node in self.ends:
				theme.update(self.theme['end'])
			if node.exdir:
				theme.update(self.theme['export'])
			if node.resume:
				theme.update(self.theme[node.resume])
			theme['tooltip'] = node.desc
			dotstr.append('    "%s" [%s]' % (node.name(False), ' '.join(['%s="%s"' % (k,theme[k]) for k in sorted(theme.keys())])))
		return dotstr

	def _dotlinks(self):
		"""
		Convert links to dot language.
		@returns:
			The string in dot language for all links.
		"""
		dotstr = []
		for node1, node2 in self.links:
			dotstr.append('    "%s" -> "%s"' % (node1.name(False), node2.name(False)))
		return dotstr

	def _dotgroups(self):
		"""
		Convert groups to dot language.
		@returns:
			The string in dot language for all groups.
		"""
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
		"""
		Generate the flowchart.
		"""
		dotstr  = ['digraph PyPPL {']
		dotstr.extend(self._dotnodes())
		dotstr.extend(self._dotlinks())
		dotstr.extend(self._dotgroups())
		dotstr.append('}')

		with open(self.dotfile, 'w') as fout:
			fout.write('\n'.join(dotstr) + '\n')
		
		try:
			rc = utils.dumbPopen(self.command).wait()
		except Exception:
			rc = 1
		if rc != 0:
			raise ValueError('Failed to generate flowcart file: %s.' % self.command)



		