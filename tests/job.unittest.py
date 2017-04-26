import unittest
import sys
import os, shutil, logging
logging.basicConfig (level = logging.DEBUG)
from time import sleep
rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, rootdir)
from pyppl import utils, job

class TestJob (unittest.TestCase):

	def testInit (self):
		j = job (0, "./", None)
		self.assertEqual (j.script, "./scripts/script.0")
		self.assertEqual (j.rcfile, "./scripts/script.0.rc")
		self.assertEqual (j.outfile, "./scripts/script.0.stdout")
		self.assertEqual (j.errfile, "./scripts/script.0.stderr")
		self.assertEqual (j.input,  {'var':[], 'file':[], 'files':[]})
		self.assertEqual (j.output, {'var':[], 'file':[]})
		self.assertEqual (j.index,  0)
	
	def testSignature (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/input")
		os.makedirs ("./test/output")
		os.makedirs ("./test/scripts")
		j = job (0, "./test/", None)
		open (j.script, 'w').write('')
		sig = j.signature()
		sleep (.1)
		open (j.script, 'w').write('')
		self.assertNotEqual (sig, j.signature())
		shutil.rmtree ("./test/")
	
	def testRc (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/input")
		os.makedirs ("./test/output")
		os.makedirs ("./test/scripts")
		j = job (0, "./test/", None)
		j.output['file'].append("./test/output/a")
		self.assertEqual (j.rc(), -9999)
		open (j.rcfile, 'w').write('')
		self.assertEqual (j.rc(), -9999)
		#open (j.rcfile, 'w').write('140')
		j.rc (140)
		self.assertEqual (open(j.rcfile).read().strip(), "1140")
		self.assertEqual (j.rc(), 140)
		j.checkOutFiles ()
		self.assertEqual (open(j.rcfile).read().strip(), "-140")
		self.assertEqual (j.rc(), -140)
		
		shutil.rmtree ("./test/")
		
	def testOutfileGenerated (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
		os.makedirs ("./test/input")
		os.makedirs ("./test/output")
		os.makedirs ("./test/scripts")
		j2 = job (1, "./test/", None)
		j2.output['file'].append ("./test/output/out.txt")
		open (j2.rcfile, 'w').write('1000')
		j2.checkOutFiles()
		self.assertEqual (j2.rc(), -1000)
		open ("./test/output/out.txt", 'w').write('')
		j2.checkOutFiles()
		shutil.rmtree ("./test/")
		
		
	def testExport (self):
		if os.path.exists ("./test/"):
			shutil.rmtree ("./test/")
			
		logger = logging.getLogger()
		def logfunc (a, b="", c=""):
			logger.info ("%s %s %s" % (a,b,c))
		os.makedirs ("./test/input")
		os.makedirs ("./test/output")
		os.makedirs ("./test/scripts")
		j3 = job (1, "./test/", logfunc)
		j3.output['file'].append ("./test/output/out.txt")
		open ("./test/output/out.txt", 'w').write('')
		
		log = []
		self.assertRaisesRegexp(ValueError, "Unable to use export cache", j3.exportCached, "", "symlink", log)
		self.assertRaisesRegexp(ValueError, "Output files not exported", j3.exportCached, "", "copy", log)
		
		e = j3.exportCached ("./test/", "copy", log)
		self.assertFalse (e)
		
		j3.export ("./test/", "copy", True)
		self.assertTrue (os.path.exists ("./test/out.txt"))
		e = j3.exportCached ("./test/", "copy", log)
		self.assertTrue (e)
		self.assertTrue (os.path.islink ("./test/output/out.txt"))
		
		shutil.rmtree ("./test/")
		os.makedirs ("./test/input")
		os.makedirs ("./test/output")
		os.makedirs ("./test/scripts")
		j4 = job (4, "./test/", logfunc)
		j4.output['file'].append ("./test/output/out.txt")
		j4.output['file'].append ("./test/output/outdir")
		open ("./test/output/out.txt", 'w').write('')
		os.makedirs ("./test/output/outdir")

		j4.export ("./test/", "gzip", True)
		
		self.assertTrue (os.path.exists ("./test/out.txt.gz"))
		self.assertTrue (os.path.exists ("./test/outdir.tgz"))
		
		e = j4.exportCached("./test/", "gzip", log)
		self.assertTrue(e)
		self.assertTrue (os.path.isfile("./test/output/out.txt"))
		self.assertTrue (os.path.isdir("./test/output/outdir"))
		
		
		shutil.rmtree ("./test/")
		
if __name__ == '__main__':
	unittest.main()
