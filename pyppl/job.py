"""
Job module for pyppl
"""
import json
from sys import stderr
from collections import OrderedDict
from glob import glob
from os import makedirs, path, remove, utime, readlink, listdir
from shutil import move, rmtree
from multiprocessing import Lock
from . import utils, logger

class Job (object):
	
	"""
	Job class, defining a job in a process
	"""
		
	def __init__(self, index, proc):
		"""
		Constructor
		@params:
			`index`:   The index of the job in a process
			`proc`:    The process
		"""
		self.dir       = path.abspath(path.join (proc.workdir, str(index)))
		self.indir     = path.join (self.dir, "input")
		self.outdir    = path.join (self.dir, "output")
		self.script    = path.join (self.dir, "job.script")
		self.rcfile    = path.join (self.dir, "job.rc")
		self.outfile   = path.join (self.dir, "job.stdout")
		self.errfile   = path.join (self.dir, "job.stderr")
		self.cachefile = path.join (self.dir, "job.cache")
		self.pidfile   = path.join (self.dir, "job.pid")
		self.index     = index
		self.proc      = proc
		self.input     = {}
		# need to pass this to next procs, so have to keep order
		self.output    = OrderedDict()
		self.brings    = {}
		self.data      = {
			'job': {
				'index'   : self.index,
				'indir'   : self.indir,
				'outdir'  : self.outdir,
				'dir'     : self.dir,
				'outfile' : self.outfile,
				'errfile' : self.errfile,
				'pidfile' : self.pidfile
			},
			'in'   : {},
			'out'  : OrderedDict(),
			'bring': {}
		}
		
	def init (self):
		"""
		Initiate a job, make directory and prepare input, brings, output and script.
		"""
		if not path.exists(self.dir):
			makedirs (self.dir)
		self.data.update (self.proc.procvars)
		self._prepInput ()
		self._prepBrings ()
		self._prepOutput ()
		self._prepScript ()

	def _reportItem(self, key, maxlen, data, loglevel):
		"""
		Report the item on logs
		@params:
			`key`: The key of the item
			`maxlen`: The max length of the key
			`data`: The data of the item
			`loglevel`: The log level
		"""
		if not isinstance(data, list):
			self.proc.log ("[%s/%s] %s => %s" % (self.index, self.proc.size - 1, key.ljust(maxlen), data), loglevel)
		else:
			ldata = len(data)
			if ldata == 0:
				self.proc.log ("[%s/%s] %s => [%s]" % (self.index, self.proc.size - 1, key.ljust(maxlen), ''), loglevel)
			elif ldata == 1:
				self.proc.log ("[%s/%s] %s => [%s]" % (self.index, self.proc.size - 1, key.ljust(maxlen), data[0]), loglevel)
			elif ldata == 2: # pragma: no cover
				self.proc.log ("[%s/%s] %s => [%s," % (self.index, self.proc.size - 1, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("[%s/%s] %s     %s]" % (self.index, self.proc.size - 1, ' '.ljust(maxlen), data[1]), loglevel)
			elif ldata == 3: # pragma: no cover
				self.proc.log ("[%s/%s] %s => [%s," % (self.index, self.proc.size - 1, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("[%s/%s] %s     %s," % (self.index, self.proc.size - 1, ' '.ljust(maxlen), data[1]), loglevel)
				self.proc.log ("[%s/%s] %s     %s]" % (self.index, self.proc.size - 1, ' '.ljust(maxlen), data[2]), loglevel)
			else:
				self.proc.log ("[%s/%s] %s => [%s," % (self.index, self.proc.size - 1, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("[%s/%s] %s     %s," % (self.index, self.proc.size - 1, ' '.ljust(maxlen), data[1]), loglevel)
				self.proc.log ("[%s/%s] %s     ...," % (self.index, self.proc.size - 1, ' '.ljust(maxlen)), loglevel)
				self.proc.log ("[%s/%s] %s     %s]" % (self.index, self.proc.size - 1, ' '.ljust(maxlen), data[-1]), loglevel)
	
	
	def report (self):
		"""
		Report the job information to logger
		"""
		maxlen = 0
		if self.input:
			maxken = max(list(map(len, self.input.keys())))
			if any([ t['type'] in self.proc.IN_FILETYPE + self.proc.IN_FILESTYPE for t in self.input.values() ]):
				maxken += 1
			maxlen = max(maxlen, maxken)
		if self.brings:
			maxken = max(list(map(len, self.brings.keys())))
			maxlen = max(maxlen, maxken)
		if self.output:
			maxken = max(list(map(len, self.output.keys())))
			maxlen = max(maxlen, maxken)

		for key in sorted(self.input.keys()):
			if self.input[key]['type'] in self.proc.IN_VARTYPE:
				self._reportItem(key, maxlen, self.input[key]['data'], 'input')
			else:
				self._reportItem(' ' + key, maxlen, self.input[key]['data'], 'input')
				self._reportItem('_' + key, maxlen, self.input[key]['orig'], 'input')
		for key in sorted(self.brings.keys(), key = lambda x: x[1:] if x.startswith('_') else x):
			self._reportItem(key if key.startswith('_') else ' ' + key, maxlen, self.brings[key], 'brings')
		for key in sorted(self.output.keys()):
			self._reportItem(key, maxlen, self.output[key]['data'], 'output')
	
	def done (self):
		"""
		Do some cleanup when job finished
		"""
		# have to touch the output directory so stat flushes and output files can be detected.
		if self.succeed():
			self.checkOutfiles()
		if self.succeed():
			self.export()
			self.cache()
			self.proc.log ('Job #%s done!' % self.index, 'JOBDONE')
			
	def showError (self, lenfailed = 1):
		"""
		Show the error message if the job failed.
		"""
		rc  = self.rc()
		msg = 'Output files not generated' if rc == -2 else \
			  'Expectations not met' if rc == -3 else       \
			  'Rc file not generated' if rc == -1 else      \
			  'Failed to submit job' if rc == 99 else       \
			  'Script error'

		if self.proc.errhow == 'ignore':
			self.proc.log ('Job #%s (total %s) failed but ignored. Return code: %s (%s).' % (self.index, lenfailed, rc, msg), 'warning')
			return
		
		self.proc.log ('Job #%s (total %s) failed. Return code: %s (%s).' % (self.index, lenfailed, rc, msg), 'error')
		
		self.proc.log('Job #%s: Script: %s' % (self.index, self.script), 'error')
		self.proc.log('Job #%s: Stdout: %s' % (self.index, self.outfile), 'error')
		self.proc.log('Job #%s: Stderr: %s' % (self.index, self.errfile), 'error')
			
		if self.index not in self.proc.echo['jobs'] or 'stderr' not in self.proc.echo['type']:
			self.proc.log('Job #%s: check STDERR below:' % (self.index), 'error')
			errmsgs = []
			if path.exists (self.errfile):
				with open(self.errfile) as f:
					errmsgs = ['[ STDERR] ' + line.rstrip("\n") for line in f]
				
			if not errmsgs:
				errmsgs = ['[ STDERR] <EMPTY STDERR>']
				
			for errmsg in errmsgs[-20:] if len (errmsgs) > 20 else errmsgs:
				logger.logger.info(errmsg)
				
			if len (errmsgs) > 20:
				logger.logger.info ('[ STDERR] ... top %s line(s) hidden (see all in "%s").' % (len(errmsgs)-20, self.errfile))
	
	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		if not path.exists (self.cachefile):
			self.proc.log ("Job #%s not cached as cache file not exists." % (self.index), "debug", "CACHE_SIGFILE_NOTEXISTS")
			return False
		
		with open (self.cachefile) as f:
			sig    = f.read()
			if not sig:
				self.proc.log ("Job #%s not cached because previous signature is empty." % (self.index), "debug", "CACHE_EMPTY_PREVSIG")
				return False

			sigNow = self.signature()
			if not sigNow:
				self.proc.log ("Job #%s not cached because current signature is empty." % (self.index), "debug", "CACHE_EMPTY_CURRSIG")
				return False

			sigOld  = json.loads(sig)
			
			# script
			sigScriptOld = sigOld['script']
			sigScriptNow = sigNow['script']
			
			# if you have a different script, you will have a different proc suffix, and you won't compare this
			# script is newer
			if sigScriptNow[1] > sigScriptOld[1]:
				self.proc.log ("Job #%s not cached because script file newer:" % (self.index), 'debug', 'CACHE_SCRIPT_NEWER')
				self.proc.log ("- Previous: %s" % (sigScriptOld[1]), 'debug', 'CACHE_SCRIPT_NEWER')
				self.proc.log ("- Current : %s" % (sigScriptNow[1]), 'debug', 'CACHE_SCRIPT_NEWER')
				return False
			
			# input var
			sigInVarOld = sigOld['in'][self.proc.IN_VARTYPE[0]]
			sigInVarNow = sigNow['in'][self.proc.IN_VARTYPE[0]]
			for key, val in sigInVarNow.items():
				if val != sigInVarOld[key]:
					self.proc.log ("Job #%s not cached because input variable (%s) is different: " % (self.index, key), 'debug', 'CACHE_SIGINVAR_DIFF')
					self.proc.log ("- Previous: %s" % (sigInVarOld[key]), 'debug', 'CACHE_SIGINVAR_DIFF')
					self.proc.log ("- Current : %s" % (val), 'debug', 'CACHE_SIGINVAR_DIFF')
					return False
			
			# input file
			sigInFileOld = sigOld['in'][self.proc.IN_FILETYPE[0]]
			sigInFileNow = sigNow['in'][self.proc.IN_FILETYPE[0]]
			
			for key, val in sigInFileNow.items():
				if val[0] != sigInFileOld[key][0]:
					self.proc.log ("Job #%s not cached because input file (%s) is different:" % (self.index, key), 'debug', 'CACHE_SIGINFILE_DIFF')
					self.proc.log ("- Previous: %s" % (sigInFileOld[key][0]), 'debug', 'CACHE_SIGINFILE_DIFF')
					self.proc.log ("- Current : %s" % (val[0]), 'debug', 'CACHE_SIGINFILE_DIFF')
					return False
				if val[1] > sigInFileOld[key][1]:
					self.proc.log ("Job #%s not cached because input file (%s) is newer:" % (self.index, key), 'debug', 'CACHE_SIGINFILE_NEWER')
					self.proc.log ("- File:     %s" % (val[0]), 'debug', 'CACHE_SIGINFILE_NEWER')
					self.proc.log ("- Previous: %s" % (sigInFileOld[key][1]), 'debug', 'CACHE_SIGINFILE_NEWER')
					self.proc.log ("- Current : %s" % (val[1]), 'debug', 'CACHE_SIGINFILE_NEWER')
					return False
			
			# input files
			sigInFilesOld = sigOld['in'][self.proc.IN_FILESTYPE[0]]
			sigInFilesNow = sigNow['in'][self.proc.IN_FILESTYPE[0]]
			for key, val in sigInFilesNow.items():
				valOld    = sorted(sigInFilesOld[key])
				valNow    = sorted(val)
				filesOld  = [v[0] for v in valOld]
				filesNow  = [v[0] for v in valNow]
				if filesNow != filesOld:
					self.proc.log ("Job #%s not cached because input files (%s) are different:" % (self.index, key), 'debug', 'CACHE_SIGINFILES_DIFF')
					self.proc.log ("- Previous: %s" % (filesOld), 'debug', 'CACHE_SIGINFILES_DIFF')
					self.proc.log ("- Current : %s" % (filesNow), 'debug', 'CACHE_SIGINFILES_DIFF')
					return False
				for i, fileTsNow in enumerate(valNow):
					fileTsOld = valOld[i]
					if fileTsNow[1] > fileTsOld[1]:
						self.proc.log ("Job #%s not cached because one of input files (%s) is newer:" % (self.index, key), 'debug', 'CACHE_SIGINFILES_NEWER')
						self.proc.log ("- File:     %s" % (fileTsNow[0]), 'debug', 'CACHE_SIGINFILES_NEWER')
						self.proc.log ("- Previous: %s" % (fileTsOld[1]), 'debug', 'CACHE_SIGINFILES_NEWER')
						self.proc.log ("- Current : %s" % (fileTsNow[1]), 'debug', 'CACHE_SIGINFILES_NEWER')
						return False
			
			# output var
			sigOutVarOld = sigOld['out'][self.proc.OUT_VARTYPE[0]]
			sigOutVarNow = sigNow['out'][self.proc.OUT_VARTYPE[0]]
			for key, val in sigOutVarNow.items():
				if val != sigOutVarOld[key]:
					self.proc.log ("Job #%s not cached because output variable (%s) is different: " % (self.index, key), 'debug', 'CACHE_SIGOUTVAR_DIFF')
					self.proc.log ("- Previous: %s" % (sigOutVarOld[key]), 'debug', 'CACHE_SIGOUTVAR_DIFF')
					self.proc.log ("- Current : %s" % (val), 'debug', 'CACHE_SIGOUTVAR_DIFF')
					return False
			
			# output file
			sigOutFileOld = sigOld['out'][self.proc.OUT_FILETYPE[0]]
			sigOutFileNow = sigNow['out'][self.proc.OUT_FILETYPE[0]]
			for key, val in sigOutFileNow.items():
				if val[0] != sigOutFileOld[key][0]:
					self.proc.log ("Job #%s not cached because output file (%s) is different:" % (self.index, key), 'debug', 'CACHE_SIGOUTFILE_DIFF')
					self.proc.log ("- Previous: %s" % (sigOutFileOld[key][0]), 'debug', 'CACHE_SIGOUTFILE_DIFF')
					self.proc.log ("- Current : %s" % (val[0]), 'debug', 'CACHE_SIGOUTFILE_DIFF')
					return False
					
			# output dir
			sigOutDirOld = sigOld['out'][self.proc.OUT_DIRTYPE[0]]
			sigOutDirNow = sigNow['out'][self.proc.OUT_DIRTYPE[0]]
			for key, val in sigOutDirNow.items():
				if val[0] != sigOutDirOld[key][0]:
					self.proc.log ("Job #%s not cached because output dir (%s) is different:" % (self.index, key), 'debug', 'CACHE_SIGOUTDIR_DIFF')
					self.proc.log ("- Previous: %s" % (sigOutDirOld[key][0]), 'debug', 'CACHE_SIGOUTDIR_DIFF')
					self.proc.log ("- Current : %s" % (val[0]), 'debug', 'CACHE_SIGOUTDIR_DIFF')
					return False
			
			return True
	
	def isExptCached (self):
		"""
		Prepare to use export files as cached information
		True if succeed, otherwise False
		"""
		if self.proc.cache != 'export':
			return False
		if self.proc.exhow in self.proc.EX_LINK:
			self.proc.log ("Job not export-cached using symlink export.", "warning", "EXPORT_CACHE_USING_SYMLINK")
			return False
		if self.proc.expart and self.proc.expart[0].render(self.data):
			self.proc.log ("Job not export-cached using partial export.", "warning", "EXPORT_CACHE_USING_EXPARTIAL")
			return False
		if not self.proc.exdir:
			self.proc.log ("Job not export-cached since export directory is not set.", "debug", "EXPORT_CACHE_EXDIR_NOTSET")
			return False
		
		for _, out in self.output.items():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			exfile = path.join (self.proc.exdir, path.basename(out['data']))
			
			if self.proc.exhow in self.proc.EX_GZIP:
				if path.isdir(out['data']) or out['type'] in self.proc.OUT_DIRTYPE:
					exfile += '.tgz'
					if not path.exists(exfile):
						self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						utils.safeRemove(out['data'])
						
					makedirs(out['data'])
					utils.untargz (exfile, out['data'])
				else:
					exfile += '.gz'
					if not path.exists (exfile):
						self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						remove (out['data'])
						
					utils.ungz (exfile, out['data'])
			else:
				if not path.exists (exfile):
					self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
					return False
				if utils.samefile (exfile, out['data']):
					continue
				if path.exists (out['data']) or path.islink(out['data']):
					self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
					utils.safeRemove(out['data'])
					
				utils.safeLink(path.realpath(exfile), out['data'])
		
		# Make sure no need to calculate next time
		self.cache ()
		if not path.exists (self.rcfile):
			with open (self.rcfile, 'w') as f:
				f.write ('0')
		
		return True
				
	def cache (self):
		"""
		Truly cache the job (by signature)
		"""
		if not self.proc.cache:
			return
		sig  = self.signature()
		if sig:
			with open (self.cachefile, 'w') as f:
				f.write (sig if not sig else json.dumps(sig))
			
	def succeed (self):
		"""
		Tell if the job is successful by return code, and output file expectations.
		@returns:
			True if succeed else False
		"""
		return self.rc() in self.proc.rc
		
	def signature (self):
		"""
		Calculate the signature of the job based on the input/output and the script
		@returns:
			The signature of the job
		"""
		ret = {}
		sig = utils.filesig (self.script)
		if not sig:
			self.proc.log ('Job #%s: Empty signature because of script file: %s.' % (self.index, self.script), 'debug', 'CACHE_EMPTY_CURRSIG')
			return ''
		ret['script'] = sig
		ret['in']     = {
			self.proc.IN_VARTYPE[0]:   {},
			self.proc.IN_FILETYPE[0]:  {},
			self.proc.IN_FILESTYPE[0]: {}
		}
		ret['out']    = {
			self.proc.OUT_VARTYPE[0]:  {},
			self.proc.OUT_FILETYPE[0]: {},
			self.proc.OUT_DIRTYPE[0]:  {}
		}
		
		for key, val in self.input.items():
			if val['type'] in self.proc.IN_VARTYPE:
				ret['in'][self.proc.IN_VARTYPE[0]][key] = val['data']
			elif val['type'] in self.proc.IN_FILETYPE:
				sig = utils.filesig (val['data'])
				if not sig:
					self.proc.log ('Job #%s: Empty signature because of input file: %s.' % (self.index, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
					return ''
				ret['in'][self.proc.IN_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.IN_FILESTYPE:
				ret['in'][self.proc.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = utils.filesig (infile)
					if not sig:
						self.proc.log ('Job #%s: Empty signature because of one of input files: %s.' % (self.index, infile), 'debug', 'CACHE_EMPTY_CURRSIG')
						return ''
					ret['in'][self.proc.IN_FILESTYPE[0]][key].append (sig)
		
		for key, val in self.output.items():
			if val['type'] in self.proc.OUT_VARTYPE:
				ret['out'][self.proc.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in self.proc.OUT_FILETYPE:
				sig = utils.filesig (val['data'])
				if not sig:
					self.proc.log ('Job #%s: Empty signature because of output file: %s.' % (self.index, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
					return ''
				ret['out'][self.proc.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.OUT_DIRTYPE:
				sig = utils.filesig (val['data'])
				if not sig:
					self.proc.log ('Job #%s: Empty signature because of output dir: %s.' % (self.index, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
					return ''
				ret['out'][self.proc.OUT_DIRTYPE[0]][key] = sig
				
		return ret
	
	def rc (self, val = None):
		"""
		Get/Set the return code
		@params:
			`val`: The return code to be set. If it is None, return the return code. Default: `None`
			If val == -1000: the return code will be negative of current one. 0 will be '-0'
		@returns:
			The return code if `val` is `None`
			If rcfile does not exist or is empty, return 9999, otherwise return -rc
			A negative rc (including -0) means output files not generated
		"""
		if val is None:
			if not path.exists (self.rcfile):
				return -1
			
			with open (self.rcfile) as f:
				return int(f.read().strip())
		else:
			with open (self.rcfile, 'w') as f:
				f.write (str(val))

	def pid (self, val = None):
		"""
		Get/Set the job id (pid or the id from queue system)
		@params:
			`val`: The id to be set
		"""
		if val is None:
			if not path.exists (self.pidfile):
				return ''
			with open(self.pidfile) as f:
				return f.read().strip()
		else:
			with open (self.pidfile, 'w') as f:
				f.write (str(val))
	
	def checkOutfiles (self, expect = True):
		"""
		Check whether output files are generated, if not, add - to rc.
		"""
		utime (self.outdir, None)
		for _, out in self.output.items():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			if not path.exists(out['data']):
				self.rc(-2)
				self.proc.log ('Job #%-3s: outfile not generated: %s' % (self.index, out['data']), 'debug', 'OUTFILE_NOT_EXISTS')
				return
		
		expectCmd = self.proc.expect.render(self.data)
		if expectCmd and expect:
			self.proc.log ('Job #%-3s: check expectation: %s' % (self.index, expectCmd), 'debug', 'EXPECT_CHECKING')
			rc = utils.dumbPopen (expectCmd, shell=True).wait()
			if rc != 0:	self.rc(-3)

	def export (self):
		"""
		Export the output files
		"""
		if not self.proc.exdir:
			return
			
		assert path.exists(self.proc.exdir)
		assert isinstance(self.proc.expart, list)
		def overwriteRemove(e, f):
			if e:
				self.proc.log ('Job #%-3s: overwriting: %s' % (self.index, f), 'export')
				if not path.isdir (f): remove (f)
				else: rmtree (f) # pragma: no cover
			else:
				if path.islink (f): remove (f)
				self.proc.log ('Job #%-3s: exporting to: %s' % (self.index, f), 'export')
		files2ex = []
		if not self.proc.expart or (len(self.proc.expart) == 1 and not self.proc.expart[0].render(self.data)):
			for _, out in self.output.items():
				if out['type'] in self.proc.OUT_VARTYPE:
					continue
				files2ex.append (out['data'])
		else:
			for expart in self.proc.expart:
				expart = expart.render(self.data)
				if expart in self.output:
					files2ex.append (self.output[expart]['data'])
				else:
					files2ex.extend(glob(path.join(self.outdir, expart)))
		files2ex = list(set(files2ex))
		
		if self.proc.exhow in self.proc.EX_MOVE:
			# make sure file2ex exists, in case it points to the same file from all jobs
			with Lock():
				for file2ex in files2ex:
					bname  = path.basename (file2ex)
					exfile = path.join (self.proc.exdir, bname)
					self.proc.log ('Job #%-3s: exporting to: %s' % (self.index, exfile), 'export')
					utils.safeMoveWithLink (file2ex, exfile, overwrite = self.proc.exow)
		else:
			for file2ex in files2ex:
				bname  = path.basename (file2ex)
				exfile = path.join (self.proc.exdir, bname)
				
				if self.proc.exhow in self.proc.EX_GZIP:
					exfile += ('.tgz' if path.isdir(file2ex) else '.gz')
				
				# don't overwrite existing files
				if (not self.proc.exow and path.exists(exfile)) or utils.samefile(file2ex, exfile):
					self.proc.log ('Job #%-3s: skipped (target exists): %s' % (self.index, exfile),  'export')
					continue

				utils.fileExists(exfile, overwriteRemove)
				if self.proc.exhow in self.proc.EX_GZIP and path.isdir(file2ex):
					utils.targz (file2ex, exfile)
				elif self.proc.exhow in self.proc.EX_GZIP and path.isfile(file2ex):
					utils.gz (file2ex, exfile)
				elif self.proc.exhow in self.proc.EX_COPY:
					utils.safeCopy (file2ex, exfile)
				elif self.proc.exhow in self.proc.EX_LINK:
					utils.safeLink (file2ex, path.abspath(exfile))
				
	def reset (self, retry = None):
		"""
		Clear the intermediate files and output files
		"""
		#self.proc.log ('Resetting job #%s ...' % self.index, 'debug', 'JOB_RESETTING')
		if retry is not None:
			retrydir = path.join(self.dir, 'retry.' + str(retry))
			utils.safeRemove(retrydir)
			makedirs(retrydir)
		else:
			for retrydir in glob(path.join(self.dir, 'retry.*')):
				utils.safeRemove(retrydir) # pragma: no cover

		if path.exists (self.rcfile) or path.islink (self.rcfile):
			if retry is None:
				remove(self.rcfile)
			else:
				move(self.rcfile, path.join(retrydir, path.basename(self.rcfile)))
		if path.exists (self.outfile) or path.islink (self.outfile):
			if retry is None:
				remove(self.outfile)
			else:
				move(self.outfile, path.join(retrydir, path.basename(self.outfile)))
		if path.exists (self.errfile) or path.islink (self.errfile):
			if retry is None:
				remove(self.errfile)
			else:
				move(self.errfile, path.join(retrydir, path.basename(self.errfile)))
		if path.exists (self.pidfile) or path.islink (self.pidfile):
			if retry is None:
				remove(self.pidfile)
			else:
				move(self.pidfile, path.join(retrydir, path.basename(self.pidfile)))
		
		if listdir (self.outdir):
			if retry is None:
				utils.safeRemove(self.outdir)
			else:
				utils.safeMove(self.outdir, path.join(retrydir, path.basename(self.outdir)))
			makedirs(self.outdir)
			
		for _, out in self.output.items():
			if out['type'] not in self.proc.OUT_DIRTYPE: continue
			makedirs(out['data'])
			#self.proc.log ('Output directory created after reset: %s.' % out['data'], 'debug', 'OUTDIR_CREATED_AFTER_RESET')

	def _linkInfile(self, orgfile):
		"""
		Create links for input files
		@params:
			`orgfile`: The original input file
		@returns:
			The link to the original file.
		"""
		if not path.exists(orgfile):
			raise OSError('No such input file: %s' % orgfile)

		basename = path.basename (orgfile)
		infile   = path.join (self.indir, basename)
		linked   = utils.safeLink(orgfile, infile, overwrite = False)
		if linked or utils.samefile(infile, orgfile):
			return infile

		(fn, ext) = path.splitext(basename)
		existInfiles = glob (path.join(self.indir, fn + '[[]*[]]' + ext))
		if not existInfiles:
			infile = path.join (self.indir, fn + '[1]' + ext)
			utils.safeLink(orgfile, infile)
		else: # pragma: no cover
			num = 0
			for eifile in existInfiles:
				if utils.samefile(eifile, orgfile):
					num = 0
					return eifile
				n   = int(path.basename(eifile)[len(fn)+1 : -len(ext)-1])
				num = max (num, n)

			if num > 0:
				infile = path.join (self.indir, fn + '[' + str(num+1) + ']' + ext)
				utils.safeLink(orgfile, infile)
		return infile
		

	def _prepInput (self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		utils.safeRemove(self.indir)
		makedirs (self.indir)

		for key, val in self.proc.input.items():
			self.input[key] = {}
			if val['type'] in self.proc.IN_FILETYPE:
				if val['data'][self.index] == '': # pragma: no cover
					orgfile = ''
					infile  = ''
				else:
					try:
						orgfile = path.abspath(val['data'][self.index])
					except AttributeError: # pragma: no cover
						stderr.write("Input data: \n  %s: %s\n" % (key, val['data'][self.index]))
						raise
					if not path.exists(orgfile):
						raise OSError('No such input file: %s' % orgfile)

					basename = path.basename (orgfile)
					infile   = self._linkInfile(orgfile)
					if basename != path.basename(infile):
						self.proc.log ("Input file renamed: %s -> %s" % (basename, path.basename(infile)), 'warning', 'INFILE_RENAMING')
						
				self.data['in'][key]       = infile
				self.data['in']['_' + key] = orgfile
				self.input[key]['type']    = self.proc.IN_FILETYPE[0]
				self.input[key]['data']    = infile
				self.input[key]['orig']    = orgfile
				
			elif val['type'] in self.proc.IN_FILESTYPE:
				self.input[key]['type']     = self.proc.IN_FILESTYPE[0]
				self.input[key]['orig']     = []
				self.input[key]['data']     = []
				self.data['in'][key]        = []
				self.data['in']['_' + key]  = []

				if not isinstance(val['data'][self.index], list):
					raise ValueError('Expect a list for input type: files, but we got: %s' % val['data'][self.index])

				for orgfile in val['data'][self.index]:
					orgfile = path.abspath(orgfile)

					basename = path.basename (orgfile)
					infile   = self._linkInfile(orgfile)
					
					if basename != path.basename(infile):
						self.proc.log ("Input file renamed: %s -> %s" % (basename, path.basename(infile)), 'warning', 'INFILE_RENAMING')
						
					self.input[key]['orig'].append (orgfile)
					self.input[key]['data'].append (infile)
					self.data['in'][key].append (infile)
					self.data['in']['_' + key].append (orgfile)
			else:
				self.input[key]['type'] = self.proc.IN_VARTYPE[0]
				self.input[key]['data'] = val['data'][self.index]
				self.data['in'][key] = val['data'][self.index]
				
	def _prepBrings (self):
		"""
		Build the brings to bring some files to indir
		The brings can be set as: `p.brings = {"infile": "{{infile.bn}}*.bai"}`
		If you have multiple files to bring in:
		`p.brings = {"infile": "{{infile.bn}}*.bai", "infile#": "{{infile.bn}}*.fai"}`
		You can use wildcards to search the files, but only the first file will return
		To access the brings in your script: {% raw %}`{{ brings.infile }}`, `{{ brings.infile# }}`{% endraw %}
		If original input file is a link, will try to find it along each directory the link is in.
		"""
		for key, val in self.proc.brings.items():
			
			if self.input[key]['type'] not in self.proc.IN_FILETYPE:
				raise ValueError('Cannot bring files for a non-file type input.')

			orginfile                     = self.input[key]['data']
			if not path.islink(orginfile): continue

			self.brings[key]              = []
			self.brings['_' + key]        = []
			self.data['bring'][key]       = []
			self.data['bring']['_' + key] = []

			if not isinstance(val, list): val = [val]
			
			infile = readlink(orginfile)
			while path.exists(infile):
				for v in val:
					pattern = path.join(path.dirname(infile), v.render(self.data))
					bring   = glob(pattern)
					if not bring: continue
					for b in bring:
						ninbn    = path.basename(infile)
						oinbn    = path.basename(orginfile)
						dstbn    = path.basename(b)

						if ninbn != oinbn: # name changed
							ninparts    = ninbn.split('.')
							oinparts    = oinbn.split('.')
							nchgpart, ochgpart = [(ninparts[i], oinparts[i]) for i in range(len(ninparts)) if ninparts[i] != oinparts[i]][0]
							dstparts    = dstbn.split('.')
							dstparts[dstparts.index(nchgpart)] = ochgpart
							dstbn       = '.'.join(dstparts)
						
						dstfile = path.join (self.indir, dstbn)
						self.data['bring'][key].append(dstfile)
						self.data['bring']['_' + key].append(b)
						self.brings[key].append(dstfile)
						self.brings['_' + key].append(b)
						utils.safeLink(b, dstfile)
						
				if not path.islink (infile): break
				infile = readlink(infile)

			if not self.brings[key]:
				raise ValueError('No bring-file found for input file: %s' % [str(v) for v in val])
				
	def _prepOutput (self):
		"""
		Build the output data.
		Output could be:
		1. list: `['output:var:{{input}}', 'outfile:file:{{infile.bn}}.txt']`
			or you can ignore the name if you don't put it in script:
				`['var:{{input}}', 'path:{{infile.bn}}.txt']`
			or even (only var type can be ignored):
				`['{{input}}', 'file:{{infile.bn}}.txt']`
		2. str : `'output:var:{{input}}, outfile:file:{{infile.bn}}.txt'`
		3. OrderedDict: `{"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}`
		   or    `{"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}`
		for 1,2 channels will be the property channel for this proc (i.e. p.channel)
		"""
		if not path.exists (self.outdir):
			makedirs (self.outdir)
		
		output = self.proc.output
		# has to be OrderedDict
		assert isinstance(output, dict)
		# allow empty output
		if not output: return
		
		for key, val in output.items():
			(outtype, outtpl) = val
			outdata               = outtpl.render(self.data)
			self.data['out'][key] = outdata
			self.output[key] = {
				'type': outtype,
				'data': outdata
			}
			if outtype in self.proc.OUT_FILETYPE + self.proc.OUT_DIRTYPE:
				if path.isabs(outdata):
					raise ValueError('Only basename expected for output file/directory. \nBut full path assigned: \n  %s\nFor key:\n  %s' % (outdata, key))
				self.output[key]['data'] = path.join(self.outdir, outdata)
				self.data['out'][key]    = path.join(self.outdir, outdata)
	
	def _prepScript (self):
		"""
		Build the script, interpret the placeholders
		"""
		script = self.proc.script.render(self.data)
		
		write = True
		if path.exists (self.script):
			f = open (self.script)
			prevscript = f.read()
			f.close()
			# no change to happen? script change will cause a different uid for a proc
			if prevscript == script:
				write = False
				self.proc.log ("Script file exists: %s" % self.script, 'debug', 'SCRIPT_EXISTS')
		
		if write:
			with open (self.script, 'w') as f:
				f.write (script)
			
			
