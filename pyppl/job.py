"""
Job module for pyppl
"""
import json, re
from collections import OrderedDict
from glob import glob
from time import sleep
from datetime import datetime
from os import makedirs, path, remove, utime, readlink
from multiprocessing import Lock, JoinableQueue, Process, Array
from six import string_types
from . import utils, logger
from .exception import JobInputParseError, JobBringParseError, JobOutputParseError

class Jobmgr (object):
	"""
	Job Manager
	"""
	STATUS_INITIATED    = 0
	STATUS_SUBMITTING   = 1
	STATUS_SUBMITTED    = 2
	STATUS_SUBMITFAILED = 3
	STATUS_DONE         = 4
	STATUS_DONEFAILED   = 5
	
	PBAR_SIZE = 50

	def __init__(self, proc, runner):
		"""
		Job manager constructor
		@params:
			`proc`     : The process
			`runner`   : The runner class
		"""
		self.proc    = proc
		status       = []
		self.runners = OrderedDict()
		for job in proc.jobs:
			if not proc.cclean and job.index not in proc.ncjobids:
				status.append(Jobmgr.STATUS_DONE)
			else:
				status.append(Jobmgr.STATUS_INITIATED)
				self.runners[job.index] = runner(job)
		self.status  = Array('i', status, lock = Lock())
		# number of runner processes
		self.nprunner = min(proc.forks, len(self.runners))
		# number of submit processes
		self.npsubmit = min(self.nprunner, proc.forks, proc.maxsubmit)

	def allJobsDone(self):
		"""
		Tell whether all jobs are done.
		No need to lock as it only runs in one process (the watcher process)
		@returns:
			`True` if all jobs are done else `False`
		"""
		if not self.runners: return True
		return all(s in [Jobmgr.STATUS_DONE, Jobmgr.STATUS_DONEFAILED] for s in self.status)

	def progressbar(self, jid, loglevel = 'info'):
		bar     = '%s [' % self.proc.jobs[jid]._indexIndicator()
		barjobs = []
		# distribute the jobs to bars
		if self.proc.size <= Jobmgr.PBAR_SIZE:
			n, m = divmod(Jobmgr.PBAR_SIZE, self.proc.size)
			for j in range(self.proc.size):
				step = n + 1 if j < m else n
				for _ in range(step):
					barjobs.append([j])
		else:
			jobx = 0
			n, m = divmod(self.proc.size, Jobmgr.PBAR_SIZE)
			for i in range(Jobmgr.PBAR_SIZE):
				step = n + 1 if i < m else n
				barjobs.append([jobx + s for s in range(step)])
				jobx += step

		# status can only be: 
		# Jobmgr.STATUS_SUBMITTED
		# Jobmgr.STATUS_SUBMITFAILED
		# Jobmgr.STATUS_DONE
		# Jobmgr.STATUS_DONEFAILED
		# Jobmgr.STATUS_INITIATED
		ncompleted = sum(1 for s in self.status if s == Jobmgr.STATUS_DONE or s == Jobmgr.STATUS_DONEFAILED)
		nrunning   = sum(1 for s in self.status if s == Jobmgr.STATUS_SUBMITTED or s == Jobmgr.STATUS_SUBMITFAILED)

		for bj in barjobs:
			if jid in bj and self.status[jid] == Jobmgr.STATUS_INITIATED:
				bar += '-'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_SUBMITFAILED:
				bar += '!'
			elif jid in bj and (self.status[jid] in [Jobmgr.STATUS_SUBMITTING, Jobmgr.STATUS_SUBMITTED]):
				bar += '>'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_DONEFAILED:
				bar += 'x'
			elif jid in bj and self.status[jid] == Jobmgr.STATUS_DONE:
				bar += '='
			elif any(self.status[j] == Jobmgr.STATUS_INITIATED for j in bj):
				bar += '-'
			elif any(self.status[j] == Jobmgr.STATUS_SUBMITFAILED for j in bj):
				bar += '!'
			elif any(self.status[j] in [Jobmgr.STATUS_SUBMITTING, Jobmgr.STATUS_SUBMITTED] for j in bj):
				bar += '>'
			elif any(self.status[j] == Jobmgr.STATUS_DONEFAILED for j in bj):
				bar += 'x'
			else: # STATUS_DONE
				bar += '='
			
		bar += '] Done: %5.1f%% | Running: %d' % (100.0*float(ncompleted)/float(self.proc.size), nrunning)
			
		self.proc.log(bar, loglevel)
	
	def canSubmit(self):
		"""
		Tell whether we can submit jobs.
		@returns:
			`True` if we can, otherwise `False`
		"""
		if self.nprunner == 0: return True
		return sum(s in [
			Jobmgr.STATUS_SUBMITTING, 
			Jobmgr.STATUS_SUBMITTED, 
			Jobmgr.STATUS_SUBMITFAILED
		] for s in self.status) < self.nprunner

	def submitPool(self, sq):
		"""
		The pool to submit jobs
		@params:
			`sq`: The submit queue
		"""
		while True:
			# if we already have enough # jobs running, wait
			if not self.canSubmit():
				sleep(.5)
				continue

			jid = sq.get()
			if jid is None:
				sq.task_done()
				break
			
			self.status[jid] = Jobmgr.STATUS_SUBMITTING
			if self.runners[jid].submit():
				self.status[jid] = Jobmgr.STATUS_SUBMITTED
			else:
				self.status[jid] = Jobmgr.STATUS_SUBMITFAILED
			self.progressbar(jid, 'submit')
			sq.task_done()

	def runPool(self, rq, sq):
		"""
		The pool to run jobs (wait jobs to be done)
		@params:
			`rq`: The run queue
			`sq`: The submit queue
		"""
		while True:
			jid = rq.get()
			if jid is None:
				rq.task_done()
				break
			else:
				r = self.runners[jid]
				while self.status[jid]!=Jobmgr.STATUS_SUBMITTED and self.status[jid]!=Jobmgr.STATUS_SUBMITFAILED:
					sleep(.5)
				if self.status[jid]==Jobmgr.STATUS_SUBMITTED and r.run():
					self.status[jid] = Jobmgr.STATUS_DONE
				else: # submission failed
					if r.retry():
						self.status[jid] = Jobmgr.STATUS_INITIATED
						sq.put(jid)
						rq.put(jid)
					else:
						self.status[jid] = Jobmgr.STATUS_DONEFAILED
				self.progressbar(jid, 'jobdone')
				rq.task_done()

	def watchPool(self, rq, sq):
		"""
		The watchdog, checking whether all jobs are done.
		"""
		while not self.allJobsDone():
			sleep(.5)

		for _ in range(self.npsubmit):
			sq.put(None)
		for _ in range(self.nprunner):
			rq.put(None)

	def run(self):
		"""
		Start to run the jobs
		"""
		submitQ = JoinableQueue()
		runQ    = JoinableQueue()

		for rid in self.runners.keys():
			submitQ.put(rid)
			runQ.put(rid)

		for _ in range(self.npsubmit):
			p = Process(target = self.submitPool, args = (submitQ, ))
			p.daemon = True
			p.start()
		
		for _ in range(self.nprunner):
			p = Process(target = self.runPool, args = (runQ, submitQ))
			p.daemon = True
			p.start()
		
		watchp = Process(target = self.watchPool, args = (runQ, submitQ))
		watchp.daemon = True
		watchp.start()

		runQ.join()
		submitQ.join()
		watchp.join()


class Job (object):
	
	"""
	Job class, defining a job in a process
	"""
	RC_SUCCESS     = 0
	RC_NOTGENERATE = -1
	RC_NOOUTFILE   = -2
	RC_EXPECTFAIL  = -3
	RC_SUBMITFAIL  = 99

	MSG_RC_NOTGENERATE = 'Rc file not generated'
	MSG_RC_NOOUTFILE   = 'Output file not generated'
	MSG_RC_EXPECTFAIL  = 'Failed to meet the expectation'
	MSG_RC_SUBMITFAIL  = 'Failed to submit job'
	MSG_RC_OTHER       = 'Script error'
	
	LOGLOCK = Lock()
		
	def __init__(self, index, proc):
		"""
		Constructor
		@params:
			`index`:   The index of the job in a process
			`proc`:    The process
		"""
		self.dir       = path.abspath(path.join (proc.workdir, str(index + 1)))
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
		# run may come first before submit
		open(self.outfile, 'w').close()
		open(self.errfile, 'w').close()
		self.data.update (self.proc.procvars)
		self._prepInput ()
		self._prepBrings ()
		self._prepOutput ()
		self._prepScript ()

	def _indexIndicator(self):
		"""
		Get the index indicator in the log
		@returns:
			The "[001/100]" like indicator
		"""
		indexlen = len(str(self.proc.size))
		return ("[%0"+ str(indexlen) +"d/%s]") % (self.index + 1, self.proc.size)

	def _reportItem(self, key, maxlen, data, loglevel):
		"""
		Report the item on logs
		@params:
			`key`: The key of the item
			`maxlen`: The max length of the key
			`data`: The data of the item
			`loglevel`: The log level
		"""
		indexstr = self._indexIndicator()

		if not isinstance(data, list):
			self.proc.log ("%s %s => %s" % (indexstr, key.ljust(maxlen), data), loglevel)
		else:
			ldata = len(data)
			if ldata == 0:
				self.proc.log ("%s %s => [%s]" % (indexstr, key.ljust(maxlen), ''), loglevel)
			elif ldata == 1:
				self.proc.log ("%s %s => [%s]" % (indexstr, key.ljust(maxlen), data[0]), loglevel)
			elif ldata == 2: 
				self.proc.log ("%s %s => [%s," % (indexstr, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("%s %s     %s]" % (indexstr, ' '.ljust(maxlen), data[1]), loglevel)
			elif ldata == 3: 
				self.proc.log ("%s %s => [%s," % (indexstr, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("%s %s     %s," % (indexstr, ' '.ljust(maxlen), data[1]), loglevel)
				self.proc.log ("%s %s     %s]" % (indexstr, ' '.ljust(maxlen), data[2]), loglevel)
			else:
				self.proc.log ("%s %s => [%s," % (indexstr, key.ljust(maxlen), data[0]), loglevel)
				self.proc.log ("%s %s     %s," % (indexstr, ' '.ljust(maxlen), data[1]), loglevel)
				self.proc.log ("%s %s     ...," % (indexstr, ' '.ljust(maxlen)), loglevel)
				self.proc.log ("%s %s     %s]" % (indexstr, ' '.ljust(maxlen), data[-1]), loglevel)
	
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
			#self.proc.log ('Job #%s done!' % self.index, 'JOBDONE')
			
	def showError (self, totalfailed = 1):
		"""
		Show the error message if the job failed.
		"""
		indexstr = self._indexIndicator()
		rc  = self.rc()
		msg = Job.MSG_RC_NOOUTFILE   if rc == Job.RC_NOOUTFILE   else \
			  Job.MSG_RC_EXPECTFAIL  if rc == Job.RC_EXPECTFAIL  else \
			  Job.MSG_RC_NOTGENERATE if rc == Job.RC_NOTGENERATE else \
			  Job.MSG_RC_SUBMITFAIL  if rc == Job.RC_SUBMITFAIL  else \
			  Job.MSG_RC_OTHER

		if self.proc.errhow == 'ignore':
			self.proc.log ('%s failed but ignored (totally %s). Return code: %s (%s).' % (indexstr, totalfailed, rc, msg), 'warning')
			return
		
		self.proc.log ('%s failed (totally %s). Return code: %s (%s).' % (indexstr, totalfailed, rc, msg), 'error')
		
		self.proc.log('%s Script: %s' % (indexstr, self.script), 'error')
		self.proc.log('%s Stdout: %s' % (indexstr, self.outfile), 'error')
		self.proc.log('%s Stderr: %s' % (indexstr, self.errfile), 'error')
		
		# errors are not echoed, print them out
		if self.index not in self.proc.echo['jobs'] or 'stderr' not in self.proc.echo['type']:
			self.proc.log('%s check STDERR below:' % (indexstr), 'error')
			errmsgs = []
			if path.exists (self.errfile):
				with open(self.errfile) as f:
					errmsgs = ['[ STDERR] ' + line.rstrip("\n") for line in f]
				
			if not errmsgs:
				errmsgs = ['[ STDERR] <EMPTY STDERR>']
				
			for errmsg in errmsgs[-20:] if len (errmsgs) > 20 else errmsgs:
				logger.logger.info(errmsg)
				
			if len (errmsgs) > 20:
				logger.logger.info ('[ STDERR] ... top %s line(s) ignored (see all in "%s").' % (len(errmsgs)-20, self.errfile))
	
	def isTrulyCached (self):
		"""
		Check whether a job is truly cached (by signature)
		"""
		indexstr = self._indexIndicator()
		if not path.exists (self.cachefile):
			self.proc.log ("%s not cached as cache file not exists." % (indexstr), "debug", "CACHE_SIGFILE_NOTEXISTS")			
			return False
		
		with open (self.cachefile) as f:
			sig = f.read()
			
		if not sig:
			self.proc.log ("%s not cached because previous signature is empty." % (indexstr), "debug", "CACHE_EMPTY_PREVSIG")
			return False

		sigOld = json.loads(sig)
		sigNow = self.signature()
		if not sigNow:
			self.proc.log ("%s not cached because current signature is empty." % (indexstr), "debug", "CACHE_EMPTY_CURRSIG")
			return False
		
		def compareVar(osig, nsig, key, logkey):
			for k in osig.keys():
				oval = osig[k]
				nval = nsig[k]
				if nval == oval: continue
				with Job.LOGLOCK:
					self.proc.log("%s not cached because %s variable(%s) is different:" % (indexstr, key, k), 'debug', logkey)
					self.proc.log("...... - Previous: %s" % oval, 'debug', logkey)
					self.proc.log("...... - Current : %s" % nval, 'debug', logkey)
				return False
			return True
		
		def compareFile(osig, nsig, key, logkey, timekey = None):
			for k in osig.keys():
				ofile, otime = osig[k]
				nfile, ntime = nsig[k]
				if nfile == ofile and ntime <= otime: continue
				if nfile != ofile:
					with Job.LOGLOCK:
						self.proc.log("%s not cached because %s file(%s) is different:" % (indexstr, key, k), 'debug', logkey)
						self.proc.log("...... - Previous: %s" % ofile, 'debug', logkey)
						self.proc.log("...... - Current : %s" % nfile, 'debug', logkey)
					return False
				if timekey and ntime > otime:
					with Job.LOGLOCK:
						self.proc.log("%s not cached because %s file(%s) is newer: %s" % (indexstr, key, k, ofile), 'debug', timekey)
						self.proc.log("...... - Previous: %s (%s)" % (otime, datetime.fromtimestamp(otime)), 'debug', timekey)
						self.proc.log("...... - Current : %s (%s)" % (ntime, datetime.fromtimestamp(ntime)), 'debug', timekey)
					return False
			return True
		
		def compareFiles(osig, nsig, key, logkey, timekey = True):
			for k in osig.keys():
				oval = sorted(osig[k])
				nval = sorted(nsig[k])
				olen = len(oval)
				nlen = len(nval)
				for i in range(max(olen, nlen)):
					if i >= olen:
						ofile, otime = None, None
					else:
						ofile, otime = oval[i]
					if i >= nlen:
						nfile, ntime = None, None
					else:
						nfile, ntime = nval[i]
					if nfile == ofile and ntime <= otime: continue
					if nfile != ofile:
						with Job.LOGLOCK:
							self.proc.log("%s not cached because file %s is different for %s files(%s):" % (indexstr, i + 1, key, k), 'debug', logkey)
							self.proc.log("...... - Previous: %s" % ofile, 'debug', logkey)
							self.proc.log("...... - Current : %s" % nfile, 'debug', logkey)
						return False
					if timekey and ntime > otime:
						with Job.LOGLOCK:
							self.proc.log("%s not cached because file %s is newer for %s files(%s): %s" % (indexstr, i + 1, key, k, ofile), 'debug', timekey)
							self.proc.log("...... - Previous: %s (%s)" % (otime, datetime.fromtimestamp(otime)), 'debug', timekey)
							self.proc.log("...... - Current : %s (%s)" % (ntime, datetime.fromtimestamp(ntime)), 'debug', timekey)
						return False
			return True
		
		if not compareFile(
			{'script': sigOld['script']},
			{'script': sigNow['script']},
			'script',
			'',
			'CACHE_SCRIPT_NEWER'
		): return False		

		if not compareVar(
			sigOld['in'][self.proc.IN_VARTYPE[0]],
			sigNow['in'][self.proc.IN_VARTYPE[0]],
			'input',
			'CACHE_SIGINVAR_DIFF'
		): return False

		if not compareFile(
			sigOld['in'][self.proc.IN_FILETYPE[0]],
			sigNow['in'][self.proc.IN_FILETYPE[0]],
			'input',
			'CACHE_SIGINFILE_DIFF',
			'CACHE_SIGINFILE_NEWER'
		): return False

		if not compareFiles(
			sigOld['in'][self.proc.IN_FILESTYPE[0]],
			sigNow['in'][self.proc.IN_FILESTYPE[0]],
			'input',
			'CACHE_SIGINFILES_DIFF',
			'CACHE_SIGINFILES_NEWER'
		): return False

		if not compareVar(
			sigOld['out'][self.proc.OUT_VARTYPE[0]],
			sigNow['out'][self.proc.OUT_VARTYPE[0]],
			'output',
			'CACHE_SIGOUTVAR_DIFF'
		): return False

		if not compareFile(
			sigOld['out'][self.proc.OUT_FILETYPE[0]],
			sigNow['out'][self.proc.OUT_FILETYPE[0]],
			'output',
			'CACHE_SIGOUTFILE_DIFF'
		): return False
		
		if not compareFile(
			sigOld['out'][self.proc.OUT_DIRTYPE[0]],
			sigNow['out'][self.proc.OUT_DIRTYPE[0]],
			'output dir',
			'CACHE_SIGOUTDIR_DIFF'
		): return False
		self.rc(0)
		return True
	
	def isExptCached (self):
		"""
		Prepare to use export files as cached information
		True if succeed, otherwise False
		"""
		if self.proc.cache != 'export':
			return False
		if self.proc.exhow in self.proc.EX_LINK:
			self.proc.log ("Job is not export-cached using symlink export.", "warning", "EXPORT_CACHE_USING_SYMLINK")
			return False
		if self.proc.expart and self.proc.expart[0].render(self.data):
			self.proc.log ("Job is not export-cached using partial export.", "warning", "EXPORT_CACHE_USING_EXPARTIAL")
			return False
		if not self.proc.exdir:
			self.proc.log ("Job is not export-cached since export directory is not set.", "debug", "EXPORT_CACHE_EXDIR_NOTSET")
			return False

		for out in self.output.values():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			exfile = path.join (self.proc.exdir, path.basename(out['data']))
			
			if self.proc.exhow in self.proc.EX_GZIP:
				if path.isdir(out['data']) or out['type'] in self.proc.OUT_DIRTYPE:
					exfile += '.tgz'
					if not path.exists(exfile):
						self.proc.log ("Job is not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						utils.safeRemove(out['data'])
						
					makedirs(out['data'])
					utils.untargz (exfile, out['data'])
				else:
					exfile += '.gz'
					if not path.exists (exfile):
						self.proc.log ("Job is not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
						return False
					
					if path.exists (out['data']) or path.islink (out['data']):
						self.proc.log ('Overwrite file for export-caching: %s' % out['data'], 'warning', 'EXPORT_CACHE_OUTFILE_EXISTS')
						remove (out['data'])
						
					utils.ungz (exfile, out['data'])
			else:
				if not path.exists (exfile):
					self.proc.log ("Job is not export-cached since exported file not exists: %s." % exfile, "debug", "EXPORT_CACHE_EXFILE_NOTEXISTS")
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
				f.write (str(Job.RC_SUCCESS))
		
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
		indexstr = self._indexIndicator()
		ret = {}
		sig = utils.filesig (self.script)
		if not sig:
			self.proc.log ('%s Empty signature because of script file: %s.' % (indexstr, self.script), 'debug', 'CACHE_EMPTY_CURRSIG')
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
				sig = utils.filesig (val['data'], self.proc.dirsig)
				if not sig:
					self.proc.log ('%s Empty signature because of input file: %s.' % (indexstr, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
					return ''
				ret['in'][self.proc.IN_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.IN_FILESTYPE:
				ret['in'][self.proc.IN_FILESTYPE[0]][key] = []
				for infile in sorted(val['data']):
					sig = utils.filesig (infile, self.proc.dirsig)
					if not sig:
						self.proc.log ('%s Empty signature because of one of input files: %s.' % (indexstr, infile), 'debug', 'CACHE_EMPTY_CURRSIG')
						return ''
					ret['in'][self.proc.IN_FILESTYPE[0]][key].append (sig)
		
		for key, val in self.output.items():
			if val['type'] in self.proc.OUT_VARTYPE:
				ret['out'][self.proc.OUT_VARTYPE[0]][key] = val['data']
			elif val['type'] in self.proc.OUT_FILETYPE:
				sig = utils.filesig (val['data'], self.proc.dirsig)
				if not sig:
					self.proc.log ('%s Empty signature because of output file: %s.' % (indexstr, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
					return ''
				ret['out'][self.proc.OUT_FILETYPE[0]][key] = sig
			elif val['type'] in self.proc.OUT_DIRTYPE:
				sig = utils.filesig (val['data'], self.proc.dirsig)
				if not sig:
					self.proc.log ('%s Empty signature because of output dir: %s.' % (indexstr, val['data']), 'debug', 'CACHE_EMPTY_CURRSIG')
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
				return Job.RC_NOTGENERATE
			
			with open (self.rcfile) as f:
				r = f.read().strip()
				if not r: return Job.RC_NOTGENERATE
				return int(r)
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
		indexstr = self._indexIndicator()
		# make sure the cache is flushed
		utime (self.outdir, None)
		for out in self.output.values():
			if out['type'] in self.proc.OUT_VARTYPE: continue
			if not path.exists(out['data']):
				self.rc(Job.RC_NOOUTFILE)
				self.proc.log ('%s outfile not generated: %s' % (indexstr, out['data']), 'debug', 'OUTFILE_NOT_EXISTS')
				return
		
		expectCmd = self.proc.expect.render(self.data)
		if expectCmd and expect:
			self.proc.log ('%s check expectation: %s' % (indexstr, expectCmd), 'debug', 'EXPECT_CHECKING')
			rc = utils.dumbPopen (expectCmd, shell=True).wait()
			if rc != 0:	self.rc(Job.RC_EXPECTFAIL)

	def export (self):
		"""
		Export the output files
		"""
		if not self.proc.exdir:
			return
		
		indexstr = self._indexIndicator()
		assert path.exists(self.proc.exdir)
		assert isinstance(self.proc.expart, list)
		
		files2ex = []
		if not self.proc.expart or (len(self.proc.expart) == 1 and not self.proc.expart[0].render(self.data)):
			for out in self.output.values():
				if out['type'] in self.proc.OUT_VARTYPE: continue
				files2ex.append (out['data'])
		else:
			for expart in self.proc.expart:
				expart = expart.render(self.data)
				if expart in self.output:
					files2ex.append (self.output[expart]['data'])
				else:
					files2ex.extend(glob(path.join(self.outdir, expart)))

		files2ex = set(files2ex)
		for file2ex in files2ex:
			bname  = path.basename (file2ex)
			exfile = path.join (self.proc.exdir, bname)
			
			if self.proc.exhow in self.proc.EX_GZIP:
				if path.isdir(file2ex):
					exfile += '.tgz'
					utils.targz(file2ex, exfile, overwrite = self.proc.exow)
				else:
					exfile += '.gz'
					utils.gz(file2ex, exfile, overwrite = self.proc.exow)
			elif self.proc.exhow in self.proc.EX_COPY:
				utils.safeCopy(file2ex, exfile, overwrite = self.proc.exow)
			elif self.proc.exhow in self.proc.EX_LINK:
				utils.safeLink(file2ex, exfile, overwrite = self.proc.exow)
			else: # move
				if path.islink(file2ex):
					utils.safeCopy(file2ex, exfile, overwrite = self.proc.exow)
				else:
					utils.safeMoveWithLink(file2ex, exfile, overwrite = self.proc.exow)
			
			self.proc.log ('%s Exported: %s' % (indexstr, exfile), 'export')
				
	def reset (self, retry = 0):
		"""
		Clear the intermediate files and output files
		"""
		#self.proc.log ('Resetting job #%s ...' % self.index, 'debug', 'JOB_RESETTING')
		retrydir = path.join(self.dir, 'retry.' + str(retry))
		if retry:
			utils.safeRemove(retrydir)
			makedirs(retrydir)
		else:
			for retrydir in glob(path.join(self.dir, 'retry.*')):
				utils.safeRemove(retrydir) 
		
		for jobfile in [self.rcfile, self.outfile, self.errfile, self.pidfile, self.outdir]:
			mvfile = path.join(retrydir, path.basename(jobfile))
			if retry:
				utils.safeMove(jobfile, mvfile)
			else:
				utils.safeRemove(jobfile)
				
		makedirs(self.outdir)
		for out in self.output.values():
			if out['type'] in self.proc.OUT_DIRTYPE: 
				makedirs(out['data'])
				#self.proc.log ('Output directory created after reset: %s.' % out['data'], 'debug', 'OUTDIR_CREATED_AFTER_RESET')
			if out['type'] in self.proc.OUT_STDOUTTYPE:
				utils._link(self.outfile, out['data'])
			if out['type'] in self.proc.OUT_STDERRTYPE:
				utils._link(self.errfile, out['data'])

	def _linkInfile(self, orgfile):
		"""
		Create links for input files
		@params:
			`orgfile`: The original input file
		@returns:
			The link to the original file.
		"""
		basename = path.basename (orgfile)
		infile   = path.join (self.indir, basename)
		utils.safeLink(orgfile, infile, overwrite = False)
		if utils.samefile(infile, orgfile):
			return infile

		(fn, ext) = path.splitext(basename)
		existInfiles = glob (path.join(self.indir, fn + '[[]*[]]' + ext))
		if not existInfiles:
			infile = path.join (self.indir, fn + '[1]' + ext)
			utils.safeLink(orgfile, infile, overwrite = False)
		else:
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
			intype = val['type']
			indata = val['data'][self.index]
			if intype in self.proc.IN_FILETYPE:
				if not isinstance(indata, string_types):
					raise JobInputParseError(indata, 'Not a string for input type "%s"' % intype)
				if not indata:
					infile  = ''
				else:
					if not path.exists(indata):
						raise JobInputParseError(indata, 'File not exists for input type "%s"' % intype)
					
					basename = path.basename (indata)
					infile   = self._linkInfile(indata)
					if basename != path.basename(infile):
						self.proc.log ("Input file renamed: %s -> %s" % (basename, path.basename(infile)), 'warning', 'INFILE_RENAMING')

				self.data['in'][key]       = infile
				self.data['in']['_' + key] = indata
				self.input[key]['type']    = intype
				self.input[key]['data']    = infile
				self.input[key]['orig']    = indata
				
			elif intype in self.proc.IN_FILESTYPE:
				self.input[key]['type']     = intype
				self.input[key]['orig']     = []
				self.input[key]['data']     = []
				self.data['in'][key]        = []
				self.data['in']['_' + key]  = []

				if not isinstance(indata, list):
					raise JobInputParseError(indata, 'Not a list for input type "%s"' % intype)

				for data in indata:
					if not isinstance(data, string_types):
						raise JobInputParseError(data, 'Not a string for element of input type "%s"' % intype)

					if not data:
						infile  = ''
					else:
						if not path.exists(data):
							raise JobInputParseError(data, 'File not exists for element of input type "%s"' % intype)
					
						basename = path.basename (data)
						infile   = self._linkInfile(data)
						if basename != path.basename(infile):
							self.proc.log ("Input file renamed: %s -> %s" % (basename, path.basename(infile)), 'warning', 'INFILE_RENAMING')
						
					self.input[key]['orig'].append (data)
					self.input[key]['data'].append (infile)
					self.data['in'][key].append (infile)
					self.data['in']['_' + key].append (data)
			else:
				self.input[key]['type'] = intype
				self.input[key]['data'] = indata
				self.data['in'][key]    = indata
				
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
				raise JobBringParseError(self.input[key]['type'], 'Cannot bring files for a non-file type input')

			self.brings[key]              = []
			self.brings['_' + key]        = []
			self.data['bring'][key]       = []
			self.data['bring']['_' + key] = []

			if not isinstance(val, list): val = [val]

			# the file in indir
			infile  = self.input[key]['data']
			# the file specified
			orgfile = self.input[key]['orig']
			#not happening
			#if not path.islink(infile): continue
			
			inbn   = path.basename(infile)
			orgbn  = path.basename(orgfile)
			diffbn = ''
			if inbn != orgbn: # name change
				diffs = reversed(list(re.finditer(r'\[\d+\]', inbn)))
				for d in diffs:
					if inbn[:d.start()] == orgbn[:d.start()]:
						diffbn = d.group()
						break
					
			while True:
				for v in val:
					pattern = path.join(path.dirname(orgfile), v.render(self.data))
					bring   = glob(pattern)
					if not bring: continue
					for b in bring:
						dstbn, dstext = path.splitext(path.basename(b))
						dstfile = path.join(self.indir, dstbn + diffbn + dstext)
						self.data['bring'][key].append(dstfile)
						self.data['bring']['_' + key].append(b)
						self.brings[key].append(dstfile)
						self.brings['_' + key].append(b)
						utils.safeLink(b, dstfile)
				if not path.islink(orgfile): break
				orgfile = readlink(orgfile)
			
			if not self.brings[key]:
				self.data['bring'][key].append('')
				self.data['bring']['_' + key].append('')
				self.brings[key].append('')
				self.brings['_' + key].append('')
				self.proc.log('No bring-in file found for %s' % repr(key), 'warning', 'BRINGFILE_NOTFOUND')

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
			outtype, outtpl = val
			outdata               = outtpl.render(self.data)
			self.data['out'][key] = outdata
			self.output[key] = {
				'type': outtype,
				'data': outdata
			}
			if outtype in self.proc.OUT_FILETYPE + self.proc.OUT_DIRTYPE + self.proc.OUT_STDOUTTYPE + self.proc.OUT_STDERRTYPE:
				if path.isabs(outdata):
					raise JobOutputParseError(outdata, 'Absolute path not allowed for output file/dir for key %s' % repr(key))
				self.output[key]['data'] = path.join(self.outdir, outdata)
				self.data['out'][key]    = path.join(self.outdir, outdata)
				
	def _prepScript (self):
		"""
		Build the script, interpret the placeholders
		"""
		script = self.proc.script.render(self.data)
		
		write = True
		if path.isfile (self.script):
			with open(self.script) as f:
				prevscript = f.read()
			if prevscript == script:
				write = False
			else:
				self.proc.log ("Script file updated: %s" % self.script, 'debug', 'SCRIPT_EXISTS')

		if write:
			with open (self.script, 'w') as f:
				f.write (script)
			
			
