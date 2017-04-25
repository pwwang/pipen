from hashlib import md5
from glob import glob
from os import path, remove, symlink, makedirs
from shutil import rmtree, copytree, copyfile, move
from collections import OrderedDict
import gzip
import utils
import pydoc

class job (object):
	"""
	The job class, defining a job in a process
	"""
		
	def __init__(self, index, workdir, input = None, output = None):
		"""
		Constructor
		@params:
			`index`:   The index of the job in a process
			`workdir`: The workdir of the process
			`input`:   The input of the job
			`output`:  The output of the job
		"""
		self.script  = path.join (workdir, "scripts", "script.%s" % index)
		self.rcfile  = path.join (workdir, "scripts", "script.%s.rc" % index)
		self.outfile = path.join (workdir, "scripts", "script.%s.stdout" % index)
		self.errfile = path.join (workdir, "scripts", "script.%s.stderr" % index)
		self.input   = {'var':[], 'file':[], 'files':[]} if input is None else input
		self.output  = {'var':[], 'file':[]} if output is None else input
		self.index   = index
		# Whether I am newly created
		self.new     = False
		
	def signature (self, log):
		"""
		Calculate the signature of the job based on the input/output and the script
		@params:
			`log`: The log function of a process
		@returns:
			The signature of the job
		"""
		sigobj = {
			'script': self.script,
			'input':  {'in' +key:val for key, val in self.input.iteritems()},
			'output': {'out'+key:val for key, val in self.output.iteritems()},
		}
		sigobj = self._obj2sig (sigobj, '', log)
		if sigobj == False: return False
		sigobj = OrderedDict(sigobj)
		return md5 (str(sigobj)).hexdigest()
		
	
	def rc (self, val = None):
		"""
		Get/Set the return code
		@params:
			`val`: The return code to be set. If it is None, return the return code. Default: `None`
		@returns:
			The return code if `val` is `None`
		"""
		if val is None:
			ret = -99
			if not path.exists (self.rcfile): return ret
			else:
				rcstr = open (self.rcfile).read().strip()
				return ret if not rcstr else int (rcstr)
		else:
			open (self.rcfile, 'w').write (str(val))
	
	def _checkOutFiles (self):
		"""
		Check whether output files are generated
		@returns:
			True if yes, else return the file that is not generated
		"""
		for outfile in self.output['file']:
			if not path.exists (outfile):
				return outfile
		return True
	
	def status (self, validRetcodes = [0]):
		"""
		Get the status of the job
		If return code is not valid, return the code
		Otherwise return `self._checkOutFiles()`
		@params:
			`validRetcodes`: the valid return codes, default: [0]
		@returns:
			The return code if it's not in `validRetcodes`
			Otherwise `self._checkOutFiles()`
		"""
		rc = self.rc()
		if rc not in validRetcodes:
			return rc
		return self._checkOutFiles()
	
	def cache (self, cachefile, log):
		"""
		Cache the job, write the signature to the cache file
		@params:
			`cachefile`: The cachefile used to save the signature
			`log`:       The log function of the process
		"""
		sig = self.signature(log)
		open(cachefile, 'a').write ("%s\t%s\n" % (self.index, sig))
		
	def _obj2sig (self, obj, k, log):
		"""
		Convert an object to a signature
		@params:
			`obj`: The object
			`k`:   The key if the object is a value of a dictionary
			`log`: The log function of the process
		@returns:
			The signature
		"""
		if isinstance (obj, dict):
			ret = {}
			for key, val in obj.iteritems():
				sig = self._obj2sig (val, key, log)
				if sig == False: return False
				ret[key] = sig
			return ret
		elif isinstance (obj, list):
			ret = []
			for o in obj:
				sig = self._obj2sig (o, k, log)
				if sig == False: return False
				ret.append (sig)
			return ret
		else:
			if 'var' in k: return md5(str(obj)).hexdigest()
			if not path.exists(obj):
				log ("Generating signature for job #%s, but %s not exists: %s" % (self.index, k, obj), 'debug')
				return False
			return utils.fileSig (obj)

	def exportCached (self, exdir, how, warnings):
		"""
		Prepare to use export files as cached information
		@params:
			`exdir`: The export directory
			`how`:   How the export files are exported
			`warnings`: The warnings generated during the process
		@returns:
			True if succeed, otherwise False
		"""
		if how == 'symlink':
			raise ValueError ('Unable to use export cache when you export using symlink.')
		if not exdir:
			raise ValueError ('Output files not exported, cannot use them for caching.')
		
		exfiles  = [path.join (exdir, path.basename(outfile)) for outfile in self.output['file']]
		for i, exfile in enumerate(exfiles):
			outfile = self.output['file'][i]
			if how == 'gzip':
				gzfile  = exfile + '.gz'
				tgzfile = exfile + '.tgz'
				if not path.exists(gzfile) and not path.exists(tgzfile): return False
				if path.exists(outfile):
					#log ('Overwrite file/dir to use export for caching: %s' % outfile, 'warning')
					warnings.append ('Overwrite file to use export for caching: %s' % outfile)
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
					#log ('Overwrite file/dir to use export for caching: %s' % outfile, 'warning')
					warnings.append ('Overwrite file to use export for caching: %s' % outfile)
					if path.isdir (outfile): rmtree (outfile)
					else: remove (outfile)
				symlink (path.realpath(exfile), outfile)
		return True
			
	def export (self, exdir, how, ow, log):
		"""
		Export the output files
		@params:
			`exdir`: The export directory
			`how`:   How the export files are exported
			`ow`:    Whether to overwrite the existing files
			`log`:   The log function of the process
		"""
		if not exdir: return
		for outfile in self.output['file']:
			bn     = path.basename (outfile)
			target = path.join (exdir, bn)
			if how == 'gzip':
				target += ('.tgz' if path.isdir(outfile) else '.gz')
			
			doExport = True
			# remove the target if exportow == True and NOT
			#   outfile is a link and it links to the target
			# cuz removing target makes it a dead link
			if ow and path.exists(target) and not utils.isSameFile(outfile, target):
				if path.isdir (target):rmtree (target)
				else: remove (target)
			elif path.exists(target):
				log('%s (target exists, skipped)' % target, 'info', 'EXPORT')
				doExport = False
			
			if doExport:
				log ('%s (%s)' % (target, how), 'info', 'EXPORT')
				if how == 'copy':
					if path.isdir (outfile): copytree (outfile, target)
					else: copyfile (outfile, target)
				elif how == 'move':
					move (outfile, target)
					symlink(path.abspath(target), outfile) # make sure dependent proc can run
				elif how == 'symlink':
					symlink (outfile, target)
					log ('%s (%s)' % (target, how), 'info', 'EXPORT')
				elif how == 'gzip':
					if path.isdir (outfile):
						utils.targz (target, outfile)
					else:
						utils.gz (target, outfile)
				
	def clearOutput (self):
		"""
		Clear the intermediate files and output files
		"""
		if path.exists (self.rcfile):  remove(self.rcfile)
		if path.exists (self.outfile): remove(self.outfile)
		if path.exists (self.errfile): remove(self.errfile)
		for outfile in self.output['file']:
			if not path.exists (outfile) and path.islink (outfile):
				remove (outfile) # remove dead links
				continue
			if not path.exists(outfile): continue
			if path.isdir (outfile):
				rmtree (outfile)
				# keep the directory, in case the output is "outdir:dir" to force create dir
				makedirs(outfile)  
			else: remove (outfile)
			
			