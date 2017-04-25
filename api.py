#!/usr/bin/env python
"""
Generate API docs for pyppl
"""
import sys, os
sys.path.insert (0, os.path.dirname(__file__))
import pyppl

doc = """
# API
<!-- toc -->
"""

modules = ['pyppl', 'channel', 'job', 'proc', 'utils', 'aggr', 'runner_local', 'runner_ssh', 'runner_sge']

for modname in modules:
	
	module = getattr (pyppl, modname)
	doc += "\n## Module `" + modname + "`  \n"
	doc += "> "
	doc += (module.__doc__ if module.__doc__ is not None else ".").lstrip()
	doc += "\n\n"
	for m in sorted(module.__dict__.keys()):
		if m.startswith('__') and m!='__init__': continue
		mobj = getattr(module, m)
		if not callable (mobj): continue
		args = "" if not callable (mobj) or not hasattr(mobj, '__code__') else str(mobj.__code__.co_varnames[:mobj.__code__.co_argcount])
		if args.endswith (",)"): args = args[:-2] + ')'
		args = args.replace ("'", "")
		isstatic = "[@staticmethod]" if type(mobj) == type(lambda x:x) else ""
		doc += "#### `" + m + " %s %s`\n" % (args, isstatic)			
		modoc = mobj.__doc__ if mobj.__doc__ is not None else ""
		modoc = modoc.split("\n")
		for line in modoc:
			line = line.strip()
			if line.startswith ("@"):
				doc += "\n- **" + line[1:] + "**  \n"
			else:
				doc += line + "  \n"
open (os.path.join( os.path.dirname(__file__), 'docs', 'api.md' ), 'w').write (doc)
#print template
print "Done!"
			
	
