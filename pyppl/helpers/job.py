from hashlib import md5
from glob import glob
from os import path, remove, symlink, makedirs
from shutil import rmtree, copytree, copyfile, move
from collections import OrderedDict
import gzip
import utils

class job (object):
	
	def __init__(self, index, workdir, input = None, output = None):
		
		self.script  = path.join (workdir, "scripts", "script.%s" % index)
		self.rcfile  = path.join (workdir, "scripts", "script.%s.rc" % index)
		self.outfile = path.join (workdir, "scripts", "script.%s.stdout" % index)
		self.errfile = path.join (workdir, "scripts", "script.%s.stderr" % index)
		self.input   = {'var':[], 'file':[], 'files':[]} if input is None else input
		self.output  = {'var':[], 'file':[]} if output is None else input
		self.index   = index
		
	def signature (self, log):
		def obj2sig (obj, k = ''):
			if isinstance (obj, dict):
				return {key:obj2sig(val, key) for key, val in obj.iteritems()}
			elif isinstance (obj, list):
				return [obj2sig (o, k) for o in obj]
			else:
				if 'var' in k: return md5(str(obj)).hexdigest()
				if not path.exists(obj):
					log ("Job #%s, %s not exists: %s" % (self.index, k, obj), 'debug')
					return False
				return utils.fileSig (obj)
						
		sigobj = {
			'script': self.script,
			'input':  {'in' +key:val for key, val in self.input.iteritems()},
			'output': {'out'+key:val for key, val in self.output.iteritems()},
		}
		sigobj = OrderedDict(obj2sig (sigobj))
		if sigobj == False: return sigobj
		return md5 (str(sigobj)).hexdigest()
	
	def rc (self, val = None):
		if val is None:
			ret = -99
			if not path.exists (self.rcfile): return ret
			else:
				rcstr = open (self.rcfile).read().strip()
				return ret if not rcstr else int (rcstr)
		else:
			open (self.rcfile, 'w').write (str(val))
	
	# whether output files are generated
	def outfileGenerated (self):
		for outfile in self.output['file']:
			if not path.exists (outfile):
				raise Exception ('[Job#%s]: Output file not generated: %s' % (self.index, outfile))
			
	# use export as cache
	def exportCached (self, exdir, how, log):
		if how == 'symlink':
			raise ValueError ('Unable to use export cache when you export using symlink.')
		if not exdir:
			raise ValueError ('Output files not exported, cannot use them for caching.')
		
		exfiles = [path.join (exdir, path.basename(outfile)) for outfile in self.output['file']]
		for i, exfile in enumerate(exfiles):
			outfile = self.output['file'][i]
			if how == 'gzip':
				gzfile  = exfile + '.gz'
				tgzfile = exfile + '.tgz'
				if not path.exists(gzfile) and not path.exists(tgzfile): return False
				if path.exists(outfile):
					log ('Overwrite file/dir to use export for caching: %s' % outfile, 'warning')
					if path.isdir (outfile): rmtree (outfile)
					else: remove (outfile)	
				if path.exists(gzfile):
					utils.ungz (gzfile, outfile)
				elif path.exists(tgzfile):
					makedirs(outfile)
					utils.untargz (tgzfile, outfile)
			else:
				if not path.exists (exfile): return False
				if path.exists(outfile):
					log ('Overwrite file/dir to use export for caching: %s' % outfile, 'warning')
					if path.isdir (outfile): rmtree (outfile)
					else: remove (outfile)
				symlink (path.realpath(exfile), outfile)
		return True
			
	def export (self, exdir, how, ow, log):
		for outfile in self.output['file']:
			bn     = path.basename (outfile)
			target = path.join (exdir, bn)
			if how == 'gzip':
				target += ('.tgz' if path.isdir(outfile) else '.gz')
			
			if path.exists (target):
				if ow and (not path.islink (outfile) or path.realpath(outfile) != path.realpath(target)):
					if path.isdir (target):rmtree (target)
					else:
						remove (target)
				else:
					log('%s (target exists, skipped)' % target, 'warning', 'EXPORT')
			
			if not path.exists (target):
				log ('%s (%s)' % (target, how), 'info', 'EXPORT')
				if how == 'copy':
					if path.isdir (outfile): copytree (outfile, target)
					else: copyfile (outfile, target)
				elif how == 'move':
					move (outfile, target)
					symlink(target, outfile) # make sure dependent proc can run
				elif how == 'symlink':
					symlink (outfile, target)
				elif how == 'gzip':
					if path.isdir (outfile):
						utils.targz (target, outfile)
					else:
						utils.gz (target, outfile)
	
	def clearOutput (self):
		for outfile in self.output['file']:
			if not path.exists(outfile): continue
			remove (outfile)