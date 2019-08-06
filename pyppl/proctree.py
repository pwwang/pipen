"""
Manage process relations
"""
import traceback
from collections import OrderedDict
from .exception import ProcTreeProcExists, ProcTreeParseError#, ProcHideError

class ProcNode(object):
	"""@API
	The node for processes to manage relations between each other
	"""

	def __init__(self, proc):
		"""@API
		A process node constructor
		@params:
			proc (Proc): The `Proc` instance
		"""
		self.proc    = proc
		self.prev    = [] # prev nodes
		self.next    = [] # next nodes
		self.ran     = False
		self.start   = False
		self.defs    = traceback.format_stack()[:-4]

	def sameIdTag(self, proc):
		"""@API
		Check if the process has the same id and tag with me.
		@params:
			proc (Proc): The `Proc` instance
		@returns:
			(bool): Whether the proc (Proc) has the same id and tag.
		"""
		return proc.id == self.proc.id and proc.tag  == self.proc.tag

	def __repr__(self):
		return '<ProcNode(<Proc(id=%s,tag=%s) @ %s>) @ %s>' % (
			self.proc.id, self.proc.tag, hex(id(self.proc)), hex(id(self)))


class ProcTree(object):
	"""@API
	A tree of processes.

	@static variables
		NODES (OrderedDict): The processes registered.
	"""
	# all processes, key is the object id
	# use static, because we want different pipelines in the same session
	# have unique (id and tag)
	# use ordered dict, because we want to known which process is defined
	# first if there are duplicated processes with the same id and tag.
	NODES    = OrderedDict()

	def __init__(self):
		"""@API
		ProcTruee constructor
		"""
		ProcTree.reset()
		self.starts  = [] # start procs
		self.ends    = [] # end procs

	@classmethod
	def init(self):
		"""@API
		Set the status of all `ProcNode`s
		"""
		# build prevs and nexts
		for proc, node in ProcTree.NODES.items():
			if not proc.depends:
				continue
			for dep in proc.depends:
				if dep not in ProcTree.NODES:
					continue
				dnode = ProcTree.NODES[dep]
				if node not in dnode.next:
					dnode.next.append(node)
				if dnode not in node.prev:
					node.prev.append(dnode)
		# for proc, node in ProcTree.NODES.items():
		# 	if proc.hide and len(node.prev) > 1 and len(node.next) > 1:
		# 		raise ProcHideError(node.proc, 'cannot be hidden in flowchart as '
		# 			'it has both more than 1 parents and children.')

	@staticmethod
	def register(*procs):
		"""@API
		Register the process
		@params:
			*procs (Proc): The `Proc` instance
		"""
		for proc in procs:
			ProcTree.NODES[proc] = ProcNode(proc)

	@staticmethod
	def check(proc):
		"""@API
		Check whether a process with the same id and tag exists
		@params:
			proc (Proc): The `Proc` instance
		"""
		for pnode, node in ProcTree.NODES.items():
			if pnode is proc or proc not in ProcTree.NODES:
				continue
			if node.sameIdTag(proc):
				raise ProcTreeProcExists(node, ProcTree.NODES[proc])

	@staticmethod
	def getPrevStr(proc):
		"""@API
		Get the names of processes a process depends on
		@params:
			proc (Proc): The `Proc` instance
		@returns:
			(str): The names
		"""
		node = ProcTree.NODES[proc]
		prev = [prevnode.proc.name() for prevnode in node.prev]
		return 'START' if not prev else '[%s]' % ', '.join(prev)

	@staticmethod
	def getNextStr(proc):
		"""@API
		Get the names of processes depend on a process
		@params:
			proc (Proc): The `Proc` instance
		@returns:
			(str): The names
		"""
		node = ProcTree.NODES[proc]
		nexs = [nextn.proc.name() for nextn in node.next]
		return 'END' if not nexs else '[%s]' % ', '.join(nexs)

	@staticmethod
	def getNext(proc):
		"""@API
		Get next processes of process
		@params:
			proc (Proc): The `Proc` instance
		@returns:
			(list[Proc]): The processes depend on this process
		"""
		node = ProcTree.NODES[proc]
		return [nextn.proc for nextn in node.next]

	@staticmethod
	def reset():
		"""@API
		Reset the status of all `ProcNode`s
		"""
		for node in ProcTree.NODES.values():
			node.prev   = []
			node.next   = []
			node.ran    = False
			node.start  = False

	def setStarts(self, starts):
		"""@API
		Set the start processes
		@params:
			starts (list[Proc]): The start processes
		"""
		self.starts.clear()
		# may also change the ends
		# p1 -> p2
		# p3 -> p4
		# ends = [p2, p4] if starts = [p1, p3]
		# ends = [p2] if starts = [p1]
		self.ends.clear()
		for node in ProcTree.NODES.values():
			node.start = False
		for start in starts:
			# if start.hide:
			# 	raise ProcHideError(start, 'start process cannot be hidden.')
			ProcTree.NODES[start].start = True
			self.starts.append(start)

	def getStarts(self):
		"""@API
		Get the start processes
		@returns:
			(list[Proc]): The start processes
		"""
		if not self.starts:
			self.starts = [proc for proc, node in ProcTree.NODES.items() if node.start]
		return self.starts

	def getPaths(self, proc, proc0 = None):
		"""@API
		Infer the path to a process
		```
		p1 -> p2 -> p3
				p4  _/
		Paths for p3: [[p4], [p2, p1]]
		```
		@params:
			proc (Proc): The process
			proc0 (Proc): The original process, because this function runs recursively.
		@returns:
			(list[list]): The path to the process.
		"""
		node  = proc if isinstance(proc, ProcNode) else ProcTree.NODES[proc]
		proc0 = proc0 or [node]
		paths = []
		# loop each prev node
		for prevnode in node.prev:
			# if we hit some nodes that being hit before
			if prevnode in proc0:
				raise ProcTreeParseError(prevnode.proc, 'Loop dependency through')
			# start nodes
			if not prevnode.prev:
				apath = [[prevnode.proc]]
			# some nodes in-between
			else:
				# get the paths for prev node
				apath = self.getPaths(prevnode, proc0 + [prevnode])
				# add prev node back to make it paths for current node
				for pnode in apath:
				# 	if not prevnode.proc.hide or not check_hide:
					pnode.insert(0, prevnode.proc)
			# add unique path to path set
			for pnode in apath:
				if pnode not in paths:
					paths.append(pnode)
		return paths

	def getPathsToStarts(self, proc):
		"""@API
		Filter the paths with start processes
		@params:
			proc (Proc): The process
		@returns:
			(list[list]): The filtered path
		"""
		# get the full paths first
		paths  = self.getPaths(proc)
		ret    = []
		starts = self.getStarts()
		for path in paths:
			# check if any starts in the path
			overlap = [pnode for pnode in path if pnode in starts]
			# if not, this is the path we want
			if not overlap:
				continue
			# use the latest start
			index = max([path.index(pnode) for pnode in overlap])
			path  = path[:(index+1)]
			if path:
				ret.append(path)
		return ret

	def checkPath(self, proc):
		"""@API
		Check whether paths of a process can start from a start process
		@params:
			proc (Proc): The process
		@returns:
			(bool|list): `True` if all paths can pass, otherwise first failed path.
		"""
		paths  = self.getPaths(proc)
		starts = set(self.getStarts())
		for path in paths:
			if not starts & set(path):
				return path
		return True

	def getEnds(self):
		"""@API
		Get the end processes
		@returns:
			(list[Proc]): The end processes
		"""
		if self.ends:
			return self.ends

		failed_paths = []
		nodes = [ProcTree.NODES[start] for start in self.getStarts()]
		while nodes:
			# check loops
			for node in nodes:
				self.getPaths(node)

			nodes2 = []
			for node in nodes:
				if node.next:
					nodes2.extend(node.next)
					continue
				passed = self.checkPath(node)
				if passed is True and node.proc not in self.ends:
					# if node.proc.hide:
					# 	raise ProcHideError(node.proc, 'end process cannot be hidden.')
					self.ends.append(node.proc)
				elif passed is not True:
					passed.insert(0, node.proc)
					failed_paths.append(passed)
			nodes = set(nodes2)

		# didn't find any ends
		if not self.ends:
			if failed_paths:
				raise ProcTreeParseError(
					' <- '.join([fn.name() for fn in failed_paths[0]]),
					'Failed to determine end processes, one of the paths cannot go through')
			raise ProcTreeParseError(
				', '.join(start.name() for start in self.getStarts()),
				'Failed to determine end processes by start processes')
		return self.ends

	def getAllPaths(self):
		"""@API
		Get all paths of the pipeline, only used to be displayed in debug
		@yields:
			(list[Proc]): The paths (end to start).
		"""
		ret = set()
		ends = self.getEnds()
		for end in ends:
			paths = self.getPathsToStarts(end)
			if not paths:
				pnode = [end] # list is not hashable for set
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
		"""@API
		Get the process to run next
		@returns:
			(Proc): The process next to run
		"""
		#ret = []
		for proc, node in ProcTree.NODES.items():
			# already ran
			if node.ran:
				continue
			# not a start and not depends on any procs
			if not node.start and not node.prev:
				continue
			# start
			if node.start or all([pnode.ran for pnode in node.prev]):
				node.ran = True
				return proc
				#ret.append(node.proc)
		return None


