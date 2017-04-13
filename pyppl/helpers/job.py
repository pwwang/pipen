from hashlib import md5
from glob import glob
from os import path, remove, symlink, makedirs
from shutil import rmtree, copytree, copyfile, move
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
		
	def signature (self):
		sSig = utils.fileSig(self.script)
		iSig = ''
		oSig = ''
		for val in self.input['var']:
			val = str(val)
			iSig += "|var:" + md5(val).hexdigest()
		for val in self.input['file']:
			iSig += "|file:" + utils.fileSig(val)
		iSig += "|files"
		for val in self.input['files']:
			for v in val: iSig += ':' + utils.fileSig(v)
					
		for val in self.output['var']:
			val = str(val)
			oSig += "|var:" + md5(val).hexdigest()
		for val in self.output['file']:
			oSig += "|file:" + utils.fileSig(val)
		return md5(sSig + ';' + iSig + ';' + oSig).hexdigest()
	
	def rc (self):
		if not path.exists (self.rcfile): return -99 
		rccodestr = open (self.rcfile).read().strip()		
		return int(rccodestr) if rccodestr else -99
	
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
				symlink (exfile, outfile)
		return True
			
	def export (self, exdir, how, ow, log):
		for outfile in self.output['file']:
			bn     = path.basename (outfile)
			target = path.join (exdir, bn)

			if path.exists (target):
				if ow:
					if path.isdir (target):rmtree (target)
					else: remove (target)
				else:
					log('%s (target exists, skipped)' % target, 'warning')
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
						utils.targz (target + '.tgz', outfile)
					else:
						utils.gz (target + '.gz', outfile)
						