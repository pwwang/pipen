"""
flowchart module for PyPPL
"""
from os import path
from copy import deepcopy
from graphviz import Digraph

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
		'procset': {
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
		'procset': {
			'style': 'filled',
			'color': '#eeeeee', # almost white
		}
	}
}

ROOTGROUP = '__ROOT__'

class Flowchart:
	"""@API
	Draw flowchart for pipelines
	"""

	def __init__(self, fcfile, dotfile):
		"""@API
		The flowchart constructor
		@params:
			fcfile (file): The flowchart file.
			dotfile (file): The dot file.
		"""
		self.fcfile  = fcfile
		self.dotfile = dotfile
		fmt          = path.splitext(self.fcfile)[1]
		fmt          = 'svg' if not fmt else fmt[1:]
		self.graph   = Digraph('PyPPL', format = fmt)
		self.theme   = THEMES['default']
		self.nodes   = {}
		self.starts  = []
		self.ends    = []
		self.links   = []

	def setTheme(self, theme, base = 'default'):
		"""@API
		Set the theme to be used
		@params:
			theme (str|dict): The theme, could be the key of Flowchart.
				- THEMES or a dict of a theme definition.
			base (str): The base theme to be based on you pass custom theme
		"""
		if isinstance(theme, dict):
			self.theme = deepcopy(THEMES[base])
			for key, val in self.theme.items():
				val.update(theme.get(key, {}))
		else:
			self.theme = THEMES[theme]

	def addNode(self, node, role = None):
		"""@API
		Add a node to the chart
		@params:
			node (Proc): The process node
			role (str): Is it a starting node, an ending node or None. Default: `None`.
		"""
		if role == 'start' and node not in self.starts:
			self.starts.append(node)
		if role == 'end' and node not in self.ends:
			self.ends.append(node)
		gname = node.procset or ROOTGROUP
		if not gname in self.nodes:
			self.nodes[gname] = []
		if not node in self.nodes[gname]:
			self.nodes[gname].append(node)

	def addLink(self, node1, node2):
		"""@API
		Add a link to the chart
		@params:
			node1 (Proc): The first process node.
			node2 (Proc): The second process node.
		"""
		if (node1, node2) not in self.links:
			self.links.append((node1, node2))

	def _assemble(self):
		"""
		Assemble the graph for printing and rendering
		"""
		# nodes
		for group, nodes in self.nodes.items():
			graph = self.graph if group == ROOTGROUP else Digraph("cluster_%s" % group)
			for node in nodes:
				# copy the theme
				theme  = deepcopy(self.theme['base'])
				if node in self.starts:
					theme.update(self.theme['start'])
				if node in self.ends:
					theme.update(self.theme['end'])
				if node.exdir:
					theme.update(self.theme['export'])
				if node.resume:
					theme.update(self.theme[node.resume])
				if node.desc != 'No description.':
					theme['tooltip'] = node.desc
				graph.node(node.name(False), **{k:str(v) for k, v in theme.items()})
			if group != ROOTGROUP:
				graph.attr(label = group, **{k:str(v) for k,v in self.theme['procset'].items()})
				self.graph.subgraph(graph)

		# edges
		for node1, node2 in self.links:
			self.graph.edge(node1.name(False), node2.name(False))

	def generate(self):
		"""@API
		Generate the dot file and graph file.
		"""
		self._assemble()
		self.graph.save(self.dotfile)
		self.graph.render(path.splitext(self.fcfile)[0], cleanup = True)
