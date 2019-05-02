"""
Manage process relations
"""
import traceback
from collections import OrderedDict
from .exceptions import ProcTreeProcExists, ProcTreeParseError, ProcHideError

class ProcNode(object):
	"""
	The node for processes to manage relations between each other
	"""

	def __init__(self, proc):
		"""
		Constructor
		@params:
			`proc`: The `Proc` instance
		"""
		self.proc    = proc
		self.prev    = [] # prev nodes
		self.next    = [] # next nodes
		self.ran     = False
		self.start   = False
		self.defs    = traceback.format_stack()[:-4]

	def sameIdTag(self, proc):
		"""
		Check if the process has the same id and tag with me.
		@params:
			`proc`: The `Proc` instance
		@returns:
			`True` if it is.
			`False` if not.
		"""
		return proc.id == self.proc.id and proc.tag  == self.proc.tag

	def __repr__(self):
		return '<ProcNode(<Proc(id=%s,tag=%s) @ %s>) @ %s>' % (
			self.proc.id, self.proc.tag, hex(id(self.proc)), hex(id(self)))


class ProcTree(object):
	"""
	A tree of processes.
	"""
	# all processes, key is the object id
	# use static, because we want different pipelines in the same session
	# have unique (id and tag)
	# use ordered dict, because we want to known which process is defined
	# first if there are duplicated processes with the same id and tag.
	NODES    = OrderedDict()

	@staticmethod
	def register(proc):
		"""
		Register the process
		@params:
			`proc`: The `Proc` instance
		"""
		ProcTree.NODES[proc] = ProcNode(proc)

	@staticmethod
	def check(proc):
		"""
		Check whether a process with the same id and tag exists
		@params:
			`proc`: The `Proc` instance
		"""
		for pnode in ProcTree.NODES.keys():
			if pnode is proc: continue
			if ProcTree.NODES[pnode].sameIdTag(proc):
				raise ProcTreeProcExists(ProcTree.NODES[pnode], ProcTree.NODES[proc])

	@staticmethod
	def getPrevStr(proc):
		"""
		Get the names of processes a process depends on
		@params:
			`proc`: The `Proc` instance
		@returns:
			The names
		"""
		node = ProcTree.NODES[proc]
		prev = [prevnode.proc.name() for prevnode in node.prev]
		return 'START' if not prev else '[%s]' % ', '.join(prev)

	@staticmethod
	def getNextStr(proc):
		"""
		Get the names of processes depend on a process
		@params:
			`proc`: The `Proc` instance
		@returns:
			The names
		"""
		node = ProcTree.NODES[proc]
		nexs = [nn.proc.name() for nn in node.next]
		return 'END' if not nexs else '[%s]' % ', '.join(nexs)

	@staticmethod
	def getNext(proc):
		"""
		Get next processes of process
		@params:
			`proc`: The `Proc` instance
		@returns:
			The processes depend on this process
		"""
		node = ProcTree.NODES[proc]
		return [nn.proc for nn in node.next]

	@staticmethod
	def reset():
		"""
		Reset the status of all `ProcNode`s
		"""
		for node in ProcTree.NODES.values():
			node.prev   = []
			node.next   = []
			node.ran    = False
			node.start  = False

	def __init__(self):
		"""
		Constructor, set the status of all `ProcNode`s
		"""
		ProcTree.reset()
		self.starts  = [] # start procs
		self.ends    = [] # end procs
		# build prevs and nexts
		for node in ProcTree.NODES.values():
			depends = node.proc.depends
			if not depends: continue
			for dep in depends:
				dnode = ProcTree.NODES[dep]
				if node not in dnode.next:
					dnode.next.append(node)
				if dnode not in node.prev:
					node.prev.append(dnode)
		for node in ProcTree.NODES.values():
			if node.proc.hide and len(node.prev) > 1 and len(node.next) > 1:
				raise ProcHideError(node.proc,
					'cannot be hidden in flowchart as it has both more than 1 parent and child.')

	@classmethod
	def setStarts(cls, starts):
		"""
		Set the start processes
		@params:
			`starts`: The start processes
		"""
		for node in ProcTree.NODES.values():
			node.start = False
		for start in starts:
			if start.hide:
				raise ProcHideError(start, 'start process cannot be hidden.')
			ProcTree.NODES[start].start = True

	def getStarts(self):
		"""
		Get the start processes
		@returns:
			The start processes
		"""
		if not self.starts:
			self.starts = [node.proc for node in ProcTree.NODES.values() if node.start]
		return self.starts

	def getPaths(self, proc, proc0 = None, check_hide = True):
		"""
		Infer the path to a process
		@params:
			`proc`: The process
			`proc0`: The original process, because this function runs recursively.
		@returns:
			```
			p1 -> p2 -> p3
			      p4  _/
			Paths for p3: [[p4], [p2, p1]]
			```
		"""
		node  = proc if isinstance(proc, ProcNode) else ProcTree.NODES[proc]
		proc0 = proc0 or [node]
		paths = []
		for prevnode in node.prev:
			if prevnode in proc0:
				raise ProcTreeParseError(prevnode.proc, 'Loop dependency through')
			if not prevnode.prev:
				# starting
				apath = [[prevnode.proc]]
			else:
				apath = self.getPaths(prevnode, proc0 + [prevnode], check_hide = check_hide)
				for pnode in apath:
					if not prevnode.proc.hide:
						pnode.insert(0, prevnode.proc)
			for pnode in apath:
				if pnode not in paths:
					paths.append(pnode)
		return paths

	def getPathsToStarts(self, proc, check_hide = True):
		"""
		Filter the paths with start processes
		@params:
			`proc`: The process
		@returns:
			The filtered path
		"""
		paths  = self.getPaths(proc, check_hide = check_hide)
		ret    = []
		starts = self.getStarts()
		for path in paths:
			overlap = [pnode for pnode in path if pnode in starts]
			if not overlap: continue
			index   = max([path.index(pnode) for pnode in overlap])
			path    = path[:(index+1)]
			if path:
				ret.append(path[:(index+1)])
		return ret

	def checkPath(self, proc):
		"""
		Check whether paths of a process can start from a start process
		@params:
			`proc`: The process
		@returns:
			`True` if all paths can pass
			The failed path otherwise
		"""
		paths  = self.getPaths(proc, False)
		starts = set(self.getStarts())
		passed = True
		for path in paths:
			if not starts & set(path):
				passed = path
				break
		return passed

	def getEnds(self):
		"""
		Get the end processes
		@returns:
			The end processes
		"""
		if self.ends:
			return self.ends

		failed_paths = []
		nodes = [ProcTree.NODES[start] for start in self.getStarts()]
		while nodes:
			# check loops
			for node in nodes: self.getPaths(node, False)

			nodes2 = []
			for node in nodes:
				if not node.next:
					passed = self.checkPath(node)
					if passed is True:
						if node.proc not in self.ends:
							if node.proc.hide:
								raise ProcHideError(node.proc, 'end process cannot be hidden.')
							self.ends.append(node.proc)
					else:
						passed.insert(0, node.proc)
						failed_paths.append(passed)
				else:
					nodes2.extend(node.next)
			nodes = set(nodes2)

		# didn't find any ends
		if not self.ends:
			if failed_paths:
				raise ProcTreeParseError(
					' <- '.join([fn.name() for fn in failed_paths[0]]), 
					'Failed to determine end processes, one of the paths cannot go through')
			else:
				raise ProcTreeParseError(
					', '.join(start.name() for start in self.getStarts()),
					'Failed to determine end processes by start processes')
		return self.ends

	def getAllPaths(self):
		"""
		Get all paths of the pipeline
		"""
		ret = set()
		ends = self.getEnds()
		for end in ends:
			paths = self.getPathsToStarts(end)
			if not paths:
				pnode = [end]
				pstr = str(pnode)
				if pstr not in ret:
					yield [end]
					ret.add(pstr)
			else:
				for pnode in paths:
					pnode = [end] + pnode
					pstr = str(pnode)
					if pstr not in ret:
						yield pnode
						ret.add(pstr)

	@classmethod
	def getNextToRun(cls):
		"""
		Get the process to run next
		@returns:
			The process next to run
		"""
		#ret = []
		for node in ProcTree.NODES.values():
			# already ran
			if node.ran:
				continue
			# not a start and not depends on any procs
			if not node.start and not node.prev:
				continue
			# start
			if node.start or all([pnode.ran for pnode in node.prev]):
				node.ran = True
				return node.proc
				#ret.append(node.proc)
		return None

	def unranProcs(self):
		"""
		Get the unran processes.
		@returns:
			The processes haven't run.
		"""
		ret = {}
		starts = set(self.getStarts())
		for node in ProcTree.NODES.values():
			# just for possible end process
			if node.next:
				continue
			# don't report obsolete process
			if not self.getPathsToStarts(node, check_hide = False):
				continue
			# check paths can't reach
			paths = self.getPaths(node, False)
			for apath in paths:
				# the path can be reached
				if set(apath) & set(starts):
					continue
				ret[node.proc.name()] = [pnode.name() for pnode in apath]
				break
		return ret
