#!/usr/bin/env python
"""
Generate API docs for PyPPL
"""
import importlib, inspect, re
from os import path
from collections import OrderedDict
from pyppl.logger import logger

def loadModule(modname, excludes = None, global_excludes = None):
	excludes        = set(excludes or [])
	global_excludes = set(global_excludes or [])
	mod             = importlib.import_module('pyppl.' + modname if modname else 'pyppl')
	funcnames       = set(dir(mod)) - excludes - global_excludes
	ret             = OrderedDict()

	excludes1 = excludes | global_excludes
	for funcname in funcnames:
		if any([re.match(ex, funcname) for ex in excludes1]):
			continue
		
		obj = getattr(mod, funcname)
		if not hasattr(obj, '__doc__') or not obj.__doc__:
			continue
		
		if inspect.isclass(obj):
			class_excludes = set([
				ex[(len(funcname) + 1):] for ex in excludes if ex.startswith(funcname + '.')
			]) | global_excludes

			ret[funcname] = obj
			parent = obj.__bases__[0]
			classfuncs = OrderedDict()
			for name in sorted(set(dir(obj)) - class_excludes):
				if any([re.match(ex, name) for ex in class_excludes]):
					continue
				func = getattr(obj, name)
				# inherited methods
				if  hasattr(parent, name) and getattr(parent, name) == getattr(obj, name):
					continue
				if not callable(func) or not hasattr(func, '__doc__') or not obj.__doc__:
					continue
				classfuncs[name] = func
			ret['class.' + funcname] = classfuncs
		elif inspect.isfunction(obj):
			ret[funcname] = obj
	return mod, ret

def formatDoc(func, name, level = None):
	try:
		args = tuple(inspect.getargspec(func))
	except TypeError:
		args = ('', None, None)

	strargs  = args[0]
	if args[1] is not None: 
		strargs.append("*" + str(args[1]))
	if args[2] is not None: 
		strargs.append("**" + str(args[2]))

	ret = ''
	if level and 'method' in level and inspect.isfunction(func):
		level = level.replace('method', 'staticmethod')
	if level and ('class' in level or 'function' in level):
		ret = '!!! example "{}: `{}`"\n'.format(level, name)
	elif level and 'staticmethod' in level:
		ret = '\t!!! tip "{}: `{} ({})`"\n'.format(level, name, ", ".join(strargs))
	elif level and 'method' in level:
		ret = '\t!!! abstract "{}: `{} ({})`"\n'.format(level, name, ", ".join(strargs))
	elif level:
		ret = "{}: `{} ({})`\n".format(level, name, ", ".join(strargs))
	modoc = func.__doc__ if func.__doc__ is not None else ""
	modoc = modoc.split("\n")
	for line in modoc:
		line = line.rstrip()
		if line.lstrip().startswith ("@"):
			p1, p2 = line.split('@', 1)
			ret += "\n{}- **{}**  \n".format(p1, p2)
		else:
			ret += line + "  \n"
	return ret

if __name__ == '__main__':
	modules = [
		('', [r'[^P].+', 'Parameters', 'ProcTree', 'Proc']),
		('proc', ['Channel', 'Jobmgr', 'Job', 'Aggr']),
		'aggr',
		('channel', [
			'Channel.append', 'Channel.count', 'Channel.extend',
			'Channel.extend', 'Channel.pop', 'Channel.remove', 'Channel.reverse',
			'Channel.sort',
		]),
		'flowchart',
		('job', ['Box']),
		('jobmgr', ['Job$', 'Queue', 'QueueEmpty', 'JobBuildingException', 'JobSubmissionException', 'JobFailException', 'ThreadPool']),
		('logger', ['Box', 'TemplateLiquid']),
		('parameters', ['Box']),
		('proctree', ['ProcTreeProcExists']),
		#('runners.helpers', ['Box', 'SafeFs']),
		'runners.runner',
		('runners.runner_dry', ['Runner$', 'Proc']),
		('runners.runner_local', ['Runner$']),
		('runners.runner_sge', ['Runner$']),
		('runners.runner_slurm', ['Runner$']),
		('runners.runner_ssh', ['Runner$']),
		('template', ['Liquid']),
		('utils', ['Box', 'Queue']),
		('utils.box', ['Box.fromkeys']),
		('utils.cmd', ['Timeout', 'ResourceWarning']),
		'utils.parallel',
		('utils.ps', ['Cmd']),
		'utils.safefs',
		('utils.taskmgr', ['Thread$', 'PriorityQueue'])
	]
	global_excludes = [
		'pycopy',
		'as_completed',
		'string_types',
		'OrderedDict',
		'cpu_count',
		'makedirs',
		'rmtree',
		'glob',
		'format_exc',
		'deepcopy',
		'Digraph',
		'datetime',
		'copytree',
		'JoinableQueue',
		'copyfileobj',
		'Lock',
		'Array',
		'Value',
		'shmove',
		'copyfile',
		'walk',
		'list2cmdline',
		'Process',
		'__subclasshook__',
		'__eq__',
		'__ne__',
		'__hash__',
		'__repr__',
		'__str__',
		'__init_subclass__', # py3
		r'^_[^\_].+',
		r'.+Error$', 
	]
	with open(path.join(path.dirname(__file__), 'docs', 'api.md'), 'w') as fout:
		for module in modules:
			if not isinstance(module, tuple):
				modname, excludes = module, None
			elif len(module) == 1:
				modname, excludes = module[0], None
			else:
				modname, excludes = module

			logger.info('Handling module: {}'.format(modname))
			mod, mods = loadModule(modname, excludes, global_excludes)
			fout.write('# module: pyppl{}\n'.format('.' + modname if modname else ''))
			fout.write(formatDoc(mod, modname))
			
			for mname, mod in mods.items():
				if isinstance(mod, dict):
					for key, val in mod.items():
						logger.info('Handling   - method: {}'.format(key))
						fout.write(formatDoc(val, key, 'method'))
				else:
					logger.info('Handling - class/function: {}'.format(mname))
					fout.write(formatDoc(mod, mname, '{}'.format('class' if 'class.' + mname in mods else 'function')))
		
