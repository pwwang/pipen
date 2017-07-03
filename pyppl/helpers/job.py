"""
Job module for pyppl
"""
import json
import sys
from collections import OrderedDict
from glob import glob
from os import makedirs, path, remove, symlink, utime, readlink, listdir
from shutil import copyfile, copytree, move, rmtree
from subprocess import Popen, PIPE

from . import utils

class job (object):
	
	"""
	Job class, defining a job in a process

	@static variables:
		`FAILED_RC`: Jobs failed to submit, no return code available
		`EMPTY_RC`:  Rc file not generated, not is empty
		`NOOUT_RC`:  Outfile not generated
		`RC_MSGS`:   The messages when job failed
	"""
	
	FAILED_RC = 9999
	EMPTY_RC  = 9998
	NOOUT_RC  = -1000
	RC_MSGS   = {
		9998:  "No rcfile generated or empty",
		9999:  "Failed to submit/run the jobs",
		-1000: "Output files not generated or expections didn't meet",
		1:     "Script error"
	}
		
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
		self.oscript   = path.join (self.dir, "job.oscript")
		self.rcfile    = path.join (self.dir, "job.rc")
		self.outfile   = path.join (self.dir, "job.stdout")
		self.errfile   = path.join (self.dir, "job.stderr")
		self.cachefile = path.join (self.dir, "job.cache")
		self.idfile    = path.join (self.dir, "job.id")
		#self.input   = {'var':[], 'file':[], 'files':[]} if input is None else input
		#self.output  = {'var':[], 'file':[]} if output is None else input
		self.index     = index
		self.proc      = proc
		self.input     = {}
		# need to pass this to next procs, so have to keep order
		self.output    = OrderedDict()
		self.brings    = {}
		self.data      = {
			'#':           index,
			'job.index':   index,
			'job.id':      '',
			'job.indir':   self.indir,
			'job.outdir':  self.outdir,
			'job.dir':     self.dir,
			'job.outfile': self.outfile,
			'job.errfile': self.errfile,
			'job.idfile':  self.idfile
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

	def report (self):
		"""
		Report the job information to logger
		"""
		for key in sorted(self.input.keys()):
			self.proc.log ("[%s/%s] %s => %s" % (self.index, self.proc.length - 1, key, self.input[key]['data']), 'info', 'input')
			if 'orig' in self.input[key]:
				self.proc.log ("[%s/%s] %s.orig => %s" % (self.index, self.proc.length - 1, key, self.input[key]['orig']), 'info', 'input')
		for key in sorted(self.brings.keys()):
			self.proc.log ("[%s/%s] %s => %s" % (self.index, self.proc.length - 1, key, self.brings[key]), 'info', 'brings')	
		for key in sorted(self.output.keys()):
			self.proc.log ("[%s/%s] %s => %s" % (self.index, self.proc.length - 1, key, self.output[key]['data']), 'info', 'output')	
	
	def done (self):
		"""
		Do some cleanup when job finished
		"""
		# have to touch the output directory so stat flushes and output files can be detected.
		utime (self.dir, None)
		self.checkOutfiles()
		if not self.succeed():
			return
		self.export()
		self.cache()		
			
	def showError (self, lenfailed = 1):
		"""
		Show the error message if the job failed.
		"""
		rc = self.rc()
		if rc in job.RC_MSGS:
			rcmsg = job.RC_MSGS[rc]
		elif rc < 0:
			rcmsg = job.RC_MSGS[job.NOOUT_RC]
		else:
			rcmsg = job.RC_MSGS[1]
			
		if rc == self.NOOUT_RC: 
			rc = "-0"
		
		if self.proc.errorhow == 'ignore':
			self.proc.log ("Job #%s (total %s) failed but ignored. Return code is %s (%s)." % (self.index, lenfailed, rc, rcmsg), "warning")
		else:
			self.proc.log ('Job #%s (total %s) failed. Return code: %s (%s).' % (self.index, lenfailed, rc, rcmsg), 'error')
		
		if not self.proc.echo:
			self.proc.log('Job #%s: check STDERR below:' % (self.index), 'error')
			
			errmsgs = []
			if path.exists (self.errfile):
				errmsgs = ['[ STDERR] ' + line.rstrip("\n") for line in open(self.errfile)]
				
			if not errmsgs:
				errmsgs = ['[ STDERR] <EMPTY STDERR>']
				
			for errmsg in errmsgs[-20:] if len (errmsgs) > 20 else errmsgs:
				self.proc.logger.error(errmsg)
				
			if len (errmsgs) > 20:
				self.proc.logger.error ('[ STDERR] ... top %s line(s) omitted (see all in "%s").' % (len(errmsgs)-20, self.errfile))
	
	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		if not path.exists (self.cachefile):
			self.proc.log ("Job #%s not cached as cache file not exists." % (self.index), "debug", "debug", "CACHE_SIGFILE_NOTEXISTS")
			return False
		
		with open (self.cachefile) as f:
			sig    = f.read()
			if not sig: 
				self.proc.log ("Job #%s not cached because previous signature is empty." % (self.index), "debug", "debug", "CACHE_EMPTY_PREVSIG")
				return False

			sigNow = self.signature()
			if not sigNow:
				self.proc.log ("Job #%s not cached because current signature is empty." % (self.index), "debug", "debug", "CACHE_EMPTY_CURRSIG")
				return False

			sigOld  = json.loads(sig)
			keysNow = sigNow.keys()
			keysOld = sigOld.keys()
			if sorted(keysNow) != sorted(keysOld):
				self.proc.log ("Job #%s not cached due to key difference of signautres: %s (previous) and %s (current)" % (self.index, keysOld, keysNow), 'debug', 'debug', 'CACHE_SIGKEYS_DIFFER')
				return False
			for key in keysNow:
				if key == 'script':
					if sigOld[key] != sigNow[key]:
						self.proc.log ("Job #%s not cached due to script file difference: %s (previous) and %s (current)" % (self.index, sigOld[key], sigNow[key]), 'debug', 'debug', 'CACHE_SCRIPT_DIFFER')
						return False
				if key == 'in':
					inTypesOld = sigOld[key].keys()
					inTypesNow = sigNow[key].keys()
					if sorted(inTypesNow) != sorted(inTypesOld):
						self.proc.log ("Job #%s not cached due to input type difference of signautres: %s (previous) and %s (current)" % (self.index, inTypesOld, inTypesNow), 'debug', 'debug', 'CACHE_SIGINTYPES_DIFFER')
						return False
					for intype in inTypesNow:
						inKeysOld = sigOld[key][intype].keys()
						inKeysNow = sigNow[key][intype].keys()
						if sorted(inKeysOld) != sorted(inKeysNow):
							self.proc.log ("Job #%s not cached due to input key difference of signautres: %s (previous) and %s (current)" % (self.index, inKeysOld, inKeysNow), 'debug', 'debug', 'CACHE_SIGINKEYS_DIFFER')
							return False
						for inkey in inKeysNow:
							if sigOld[key][intype][inkey] != sigNow[key][intype][inkey]:
								self.proc.log ("Job #%s not cached due to input difference for key %s: %s (previous) and %s (current)" % (self.index, inkey, sigOld[key][intype][inkey], sigNow[key][intype][inkey]), 'debug', 'debug', 'CACHE_SIGINPUT_DIFFER')
								return False
				if key == 'out':
					outTypesOld = sigOld[key].keys()
					outTypesNow = sigNow[key].keys()
					if sorted(outTypesNow) != sorted(outTypesOld):
						self.proc.log ("Job #%s not cached due to output type difference of signautres: %s (previous) and %s (current)" % (self.index, outTypesOld, outTypesNow), 'debug', 'debug', 'CACHE_SIGOUTTYPES_DIFFER')
						return False
					for outtype in outTypesNow:
						outKeysOld = sigOld[key][outtype].keys()
						outKeysNow = sigNow[key][outtype].keys()
						if sorted(outKeysOld) != sorted(outKeysNow):
							self.proc.log ("Job #%s not cached due to output key difference of signautres: %s (previous) and %s (current)" % (self.index, outKeysOld, outKeysNow), 'debug', 'debug', 'CACHE_SIGOUTKEYS_DIFFER')
							return False
						for outkey in outKeysNow:
							if sigOld[key][outtype][outkey] != sigNow[key][outtype][outkey]:
								self.proc.log ("Job #%s not cached due to output difference for key %s: %s (previous) and %s (current)" % (self.index, outkey, sigOld[key][outtype][outkey], sigNow[key][outtype][outkey]), 'debug', 'debug', 'CACHE_SIGOUTPUT_DIFFER')
								return False
			return True
	
	def isExptCached (self):
		"""
		Prepare to use export files as cached information
		True if succeed, otherwise False
		"""
		if self.proc.cache != 'export':
			return False
		if self.proc.exhow in self.proc.EX_SYMLINK:
			self.proc.log ("Job not export-cached using symlink export.", "warning", "warning", "EXPORT_CACHE_USING_SYMLINK")
			return False
		if not self.proc.exdir:
			self.proc.log ("Job not export-cached since export directory is not set.", "debug", "debug", "EXPORT_CACHE_EXDIR_NOTSET")
			return False
		
		for _, out in self.output.items():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			exfile = path.join (self.proc.exdir, path.basename(out['data']))
			
			if self.proc.exhow in self.proc.EX_GZIP:
				if out['type'] in self.proc.OUT_FILETYPE:
					exfile += '.%s.gz' % self.proc._name (False)
					if not path.exists (exfile): 
						self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						remove (out['data'])
						
					utils.ungz (exfile, out['data'])
					
				elif out['type'] in self.proc.OUT_DIRTYPE:
					exfile += '.%s.tgz' % self.proc._name (False)
					if not path.exists(exfile): 
						self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export caching: %s' % out['data'], 'warning', 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						if path.islink (out['data']): remove (out['data'])
						else: rmtree (out['data'])
						
					makedirs(out['data'])
					utils.untargz (exfile, out['data'])
			else:
				if not path.exists (exfile):
					self.proc.log ("Job not export-cached since exported file not exists: %s." % exfile, "debug", "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
					return False	
				if utils.isSamefile (exfile, out['data']):
					continue
				if path.exists (out['data']):
					self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
					if not path.isdir (out['data']): remove (out['data'])
					else: rmtree (out['data'])
					
				symlink (path.realpath(exfile), out['data'])
		
		# Make sure no need to calculate next time
		self.cache ()
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
		Tell if the job is successful by return code
		"""
		return self.rc() in self.proc.retcodes
		
	def signature (self):
		"""
		Calculate the signature of the job based on the input/output and the script
		@returns:
			The signature of the job
		"""
		ret = {}
		sig = utils.filesig (self.oscript)
		if not sig: 
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
					return ''
				ret['in'][self.proc.IN_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.IN_FILESTYPE:
				ret['in'][self.proc.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = utils.filesig (infile)
					if not sig: 
						return ''
					ret['in'][self.proc.IN_FILESTYPE[0]][key].append (sig)
		
		for key, val in self.output.items():
			if val['type'] in self.proc.OUT_VARTYPE:
				ret['out'][self.proc.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in self.proc.OUT_FILETYPE:
				sig = utils.filesig (val['data'])
				if not sig: 
					return ''
				ret['out'][self.proc.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.OUT_DIRTYPE:
				sig = utils.filesig (val['data'])
				if not sig: 
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
				return job.EMPTY_RC
			
			with open (self.rcfile) as f:
				rcstr = f.read().strip()
				if rcstr == '': 
					return job.EMPTY_RC
				if rcstr == '-0': 
					return job.NOOUT_RC
				return int (rcstr)
		else:
			r = self.rc ()
			if val == job.NOOUT_RC:
				if r < 0 or r == job.FAILED_RC: 
					return
				if r > 0: 
					val = -r
				elif r == 0: 
					val = "-0"
			with open (self.rcfile, 'w') as f:
				f.write (str(val))

	def id (self, val = None):
		"""
		Get/Set the job id (pid or the id from queue system)
		@params:
			`val`: The id to be set
		"""
		if val is None:
			if not path.exists (self.idfile):
				return ''
			with open(self.idfile) as f:
				return f.read().strip()
		else:
			self.data['job.id'] = val
			with open (self.idfile, 'w') as f:
				f.write (val)
	
	def checkOutfiles (self):
		"""
		Check whether output files are generated, if not, add - to rc.
		"""
		utime (self.outdir, None)
		for _, out in self.output.items():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			if not path.exists (out['data']):
				self.rc (job.NOOUT_RC)
				return
				
		if self.proc.expect:
			expect = utils.format (self.proc.expect, self.data)
			exrc   = Popen (expect, shell=True, stdout=PIPE, stderr=PIPE).wait()
			if exrc != 0:
				self.rc (job.NOOUT_RC)
				return
			
	def export (self):
		"""
		Export the output files
		"""
		if not self.proc.exportdir: 
			return

		for _, out in self.output.items():
			if out['type'] in self.proc.OUT_VARTYPE: 
				continue

			bname  = path.basename (out['data'])
			exfile = path.join (self.proc.exportdir, bname)
			
			if self.proc.exhow in self.proc.EX_GZIP and out['type'] in self.proc.OUT_FILETYPE:
				exfile += '.%s.gz' % self.proc._name (False)
			elif self.proc.exhow in self.proc.EX_GZIP and out['type'] in self.proc.OUT_DIRTYPE:
				exfile += '.%s.tgz' % self.proc._name (False)
			
			# don't overwrite existing files
			if not self.proc.exportow and path.exists(exfile):
				self.proc.log ('Job #%-3s: skipped (target exists): %s' % (self.index, exfile), 'info', 'export')
				continue
			
			if path.exists(exfile):
				self.proc.log ('Job #%-3s: overwriting: %s' % (self.index, exfile), 'info', 'export')
				if not path.isdir (exfile): 
					remove (exfile)
				else: rmtree (exfile)
			else:
				if path.islink (exfile): 
					remove (exfile)
				self.proc.log ('Job #%-3s: exporting to: %s' % (self.index, exfile), 'info', 'export')
			
			if self.proc.exporthow in self.proc.EX_GZIP and out['type'] in self.proc.OUT_FILETYPE and not path.isdir(out['data']):
				utils.gz (exfile, out['data'])
			elif self.proc.exporthow in self.proc.EX_GZIP and (out['type'] in self.proc.OUT_DIRTYPE or (out['type'] in self.proc.OUT_FILETYPE and path.isdir(out['data']))):
				utils.targz (exfile, out['data'])
			elif self.proc.exporthow in self.proc.EX_COPY and out['type'] in self.proc.OUT_FILETYPE and not path.isdir(out['data']):
				copyfile (out['data'], exfile)
			elif self.proc.exporthow in self.proc.EX_COPY and (out['type'] in self.proc.OUT_DIRTYPE or (out['type'] in self.proc.OUT_FILETYPE and path.isdir(out['data']))):
				copytree (out['data'], exfile)
			elif self.proc.exporthow in self.proc.EX_MOVE:
				move (out['data'], exfile)
				# make sure dependent proc can run
				symlink(path.abspath(exfile), out['data'])
			elif self.proc.exporthow in self.proc.EX_SYMLINK:
				symlink (out['data'], path.abspath(exfile))
				
	def reset (self):
		"""
		Clear the intermediate files and output files
		"""
		self.proc.log ('Resetting job #%s ...' % self.index, 'debug', 'debug', 'JOB_RESETTING')
		if path.exists (self.rcfile) or path.islink (self.rcfile):
			remove(self.rcfile)
		if path.exists (self.outfile) or path.islink (self.outfile):
			remove(self.outfile)
		if path.exists (self.errfile) or path.islink (self.errfile):
			remove(self.errfile)
		if path.exists (self.idfile) or path.islink (self.idfile):
			remove(self.idfile)
		
		if listdir (self.outdir):
			rmtree  (self.outdir)	
			makedirs(self.outdir)
			
		for _, out in self.output.items():
			if out['type'] not in self.proc.OUT_DIRTYPE: 
				continue
			makedirs (out['data'])
			self.proc.log ('Output directory created after reset: %s.' % out['data'], 'debug', 'debug', 'OUTDIR_CREATED_AFTER_RESET')

	def _prepInput (self):
		"""
		Prepare input, create link to input files and set other placeholders
		"""
		if not path.exists (self.indir):
			makedirs (self.indir)
		
		for key, val in self.proc.indata.items():
			self.input[key] = {}
			if val['type'] in self.proc.IN_FILETYPE:
				origfile = path.abspath(val['data'][self.index])
				basename = path.basename (origfile)
				infile   = path.join (self.indir, basename)
				if not path.exists (infile):
					if path.islink (infile): 
						remove (infile)
					symlink (origfile, infile)
				elif not utils.isSamefile (origfile, infile):
					#bedir  = path.join (self.indir, basename + '.' + utils.uid(origfile, 4)) # basename exists
					#infile = path.join (bedir, basename)
					#if not path.exists(bedir):
					#	makedirs (bedir)
					(fn, _, ext) = basename.rpartition('.')
					infile = path.join (self.indir, fn + '._' + utils.uid(path.realpath(origfile), 4) + '_.' + ext)
					
					if path.exists (infile):
						self.proc.log ("Overwriting renamed input file: %s" % infile, 'warning', 'warning', 'INFILE_OVERWRITING')
						remove (infile)  # it's a link
						symlink (origfile, infile)
					else:
						self.proc.log ("Renaming input file: %s" % infile, 'warning', 'warning', 'INFILE_RENAMING')
						symlink (origfile, infile)
						
				self.data[key]           = infile
				self.data[key + '.orig'] = origfile
				self.input[key]['type']  = self.proc.IN_FILETYPE[0]
				self.input[key]['data']  = infile
				self.input[key]['orig']  = origfile
				
			elif val['type'] in self.proc.IN_FILESTYPE:
				self.input[key]['type'] = self.proc.IN_FILESTYPE[0]
				self.input[key]['orig'] = []
				self.input[key]['data'] = []
				for origfile in val['data'][self.index]:
					origfile = path.abspath(origfile)
					basename = path.basename (origfile)
					infile   = path.join (self.indir, basename)
					if not key in self.data: 
						self.data[key] = []
					if not key + '.orig' in self.data: 
						self.data[key + '.orig'] = []
					if not path.exists (infile):
						if path.islink (infile): 
							remove (infile)
						symlink (origfile, infile)
					elif not utils.isSamefile (origfile, infile):
						(fn, _, ext) = basename.rpartition('.')
						infile = path.join (self.indir, fn + '._' + utils.uid(path.realpath(origfile), 4) + '_.' + ext)
						
						if path.exists (infile):
							self.proc.log ("Overwriting renamed input file: %s" % infile, 'warning', 'warning', 'INFILE_OVERWRITING')
							remove (infile)  # it's a link
							symlink (origfile, infile)
						else:
							self.proc.log ("Renaming input file: %s" % infile, 'warning', 'warning', 'INFILE_RENAMING')
							symlink (origfile, infile)
						
					self.input[key]['orig'].append (origfile)
					self.input[key]['data'].append (infile)
					self.data[key].append (infile)
					self.data[key + '.orig'].append (origfile)
			else:
				self.input[key]['type'] = self.proc.IN_VARTYPE[0]
				self.input[key]['data'] = val['data'][self.index]
				self.data[key] = val['data'][self.index]
				
	def _prepBrings (self):
		"""
		Build the brings to bring some files to indir
		The brings can be set as: `p.brings = {"infile": "{{infile.bn}}*.bai"}`
		If you have multiple files to bring in:
		`p.brings = {"infile": "{{infile.bn}}*.bai", "infile#": "{{infile.bn}}*.fai"}`
		You can use wildcards to search the files, but only the first file will return
		To access the brings in your script: {% raw %}`{{ infile.bring }}`, `{{ infile#.bring }}`{% endraw %}
		If original input file is a link, will try to find it along each directory the link is in.
		"""
		for key, val in self.proc.brings.items():
			
			brkey   = "bring." + key
			pattern = utils.format (val, self.data)
			
			inkey   = key.split("#")[0]
			infile  = self.input[inkey]['data']
			intype  = self.input[inkey]['type']
			if intype not in self.proc.IN_FILETYPE:
				raise ValueError ('Only can brings a file related to an input file.')

			# Anyway give an empty string, so that users can tell if bringing fails
			self.data[brkey]           = ''
			self.data[brkey + ".orig"] = ''
			self.brings[key]           = ''
			self.brings[key + ".orig"] = ''
			while path.exists(infile):
				bring = glob (path.join (path.dirname(infile), pattern))
				if bring:
					dstfile = path.join (self.indir, path.basename(bring[0]))
					self.data[brkey] = dstfile
					self.data[brkey + ".orig"] = bring[0]
					self.brings[key] = dstfile
					self.brings[key + ".orig"] = bring[0]
					if path.exists(dstfile) and not utils.isSamefile (dstfile, bring[0]):
						self.proc.log ("Overwriting bring file: %s" % dstfile, 'warning', 'warning', 'BRINGFILE_OVERWRITING')
						remove (dstfile) # a link
						symlink (bring[0], dstfile)
					elif not path.exists(dstfile):
						if path.islink (dstfile): 
							remove (dstfile)
						symlink (bring[0], dstfile)
					break
				# should be a link, then can bring, otherwise it's in job.indir, 
				# not possible to have the bring file
				if not path.islink (infile): 
					break
				infile = readlink(infile)
				
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
		3. dict: `{"output:var:{{input}}": channel1, "outfile:file:{{infile.bn}}.txt": channel2}`
		   or    `{"output:var:{{input}}, output:file:{{infile.bn}}.txt" : channel3}`
		for 1,2 channels will be the property channel for this proc (i.e. p.channel)
		"""
		if not path.exists (self.outdir):
			makedirs (self.outdir)
			
		output = self.proc.output
		if not output:
			return
			#raise ValueError ('%s: Output is not specified' % self.proc._name())
		
		if not isinstance (output, dict):
			output = ','.join(utils.alwaysList (output))
		else:
			output = ','.join([key + ':' + val for key, val in output.items()])
			
		alltype = self.proc.OUT_VARTYPE + self.proc.OUT_FILETYPE + self.proc.OUT_DIRTYPE
		for outitem in utils.split(output, ','):
			parts   = utils.split(outitem, ':')
			outtype = self.proc.OUT_VARTYPE[0]
			if len(parts) == 1 or len(parts) > 3:
				raise ValueError ('You need name your output or you have more than 3 parts in your output items.')
			
			if len(parts) == 2:
				outkey = parts[0]
				outexp = parts[1]
				if outkey in alltype:
					self.proc.log ('You are using preseved types (%s) as output names.' % parts[0], 'warning', 'warning', 'OUTNAME_USING_OUTTYPES')
			
			else:  # len (parts) == 3
				outkey  = parts[0]
				outtype = parts[1]
				outexp  = parts[2]
				if outtype not in self.proc.OUT_VARTYPE + self.proc.OUT_FILETYPE + self.proc.OUT_DIRTYPE:
					raise ValueError ('Expect output type: %s instead of %s' % (alltype, parts[1]))
			
			if outtype not in self.proc.OUT_VARTYPE:
				outexp = path.join (self.outdir, outexp)
			
			val = utils.format (outexp, self.data)
			if outtype in self.proc.OUT_DIRTYPE and not path.exists(val):
				makedirs (val)
				self.proc.log ('Output directory created: %s.' % val, 'debug', 'debug', 'OUTDIR_CREATED')

			self.data[outkey]           = val
			self.output[outkey]         = {
				'type': outtype,
				'data': val
			}

	
	def _prepScript (self): 
		"""
		Build the script, interpret the placeholders
		"""
		script    = self.proc.script.strip()
		if not script:
			self.proc.log ('No script specified', 'warning', 'warning', 'NOSCRIPT')
			with open (self.script, 'w') as f:
				f.write ('')
			return
		
		if script.startswith ('template:'):
			tplfile = script[9:].strip()
			if not path.isabs(tplfile):
				tplfile = path.join (path.dirname(sys.argv[0]), tplfile)
			if not path.exists (tplfile):
				raise ValueError ('Script template file "%s" does not exist.' % tplfile)
			self.proc.log ("Using template file: %s" % tplfile, 'debug', 'debug', 'SCRIPT_USING_TEMPLATE')
			f = open(tplfile)
			script = f.read().strip()
			f.close()
		
		if not script.startswith ("#!"):
			script = "#!/usr/bin/env " + self.proc.defaultSh + "\n\n" + script
		
		if path.exists (self.oscript):
			f = open (self.oscript)
			oscript = f.read()
			f.close()
			# no change to happen? script change will cause a different uid for a proc
			if oscript == script:
				self.proc.log ("Script file exists: %s" % self.script, 'debug', 'debug', 'SCRIPT_EXISTS')
			else:
				with open (self.oscript, 'w') as f:
					f.write (script)
		else:
			with open (self.oscript, 'w') as f:
				f.write (script)
		
		script = utils.format (script, self.data)
		with open (self.script, 'w') as f:
			f.write (script)
			
			
