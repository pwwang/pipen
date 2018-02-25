import helpers, unittest

from os import path
from time import sleep
from Queue import Empty
from multiprocessing import JoinableQueue

from pyppl import Jobmgr, Proc, utils
from pyppl.runners import RunnerLocal

def _getItemsFromQ (q):
	ret = []
	while True:
		try:
			ret.append(q.get_nowait())
		except Empty:
			break
	return ret

class TestJobmgr(helpers.TestCase):
	
	def dataProvider_testInit(self, testdir):
		pInit = Proc()
		pInit.ppldir = testdir
		pInit.forks = 16
		pInit.nsub  = 5
		yield pInit, [], [], 0, 0 # no jobs
		
		pInit1 = Proc()
		pInit1.ppldir = testdir
		pInit1.props['ncjobids'] = [1, 2,3]
		pInit1.input = {'a': [1,2,3,4]}
		pInit1.forks = 5
		pInit1.nsub  = 2
		with helpers.log2str():
			pInit1._tidyBeforeRun()
		pInit1.jobs[0].cache()
		yield pInit1, [Jobmgr.STATUS_DONE, Jobmgr.STATUS_INITIATED, Jobmgr.STATUS_INITIATED, Jobmgr.STATUS_INITIATED], [1, 2, 3], 3, 2
		
		pInit2 = Proc()
		pInit2.ppldir = testdir
		pInit2.props['ncjobids'] = [1, 2,3]
		pInit2.input = {'a': [1,2,3,4]}
		pInit2.forks = 5
		pInit2.nsub  = 2
		pInit2.cclean = True
		with helpers.log2str():
			pInit2._tidyBeforeRun()
		pInit2.jobs[0].cache()
		yield pInit2, [Jobmgr.STATUS_INITIATED, Jobmgr.STATUS_INITIATED, Jobmgr.STATUS_INITIATED, Jobmgr.STATUS_INITIATED], [0, 1, 2, 3], 4, 2
	
	def testInit(self, proc, status, runnerkeys, nprunner, npsubmit):
		jm = Jobmgr(proc, RunnerLocal)
		self.assertIs(jm.proc, proc)
		self.assertItemEqual(jm.runners.keys(), runnerkeys)
		self.assertListEqual(list(jm.status), status)
		self.assertEqual(jm.nprunner, nprunner)
		self.assertEqual(jm.npsubmit, npsubmit)
		
	def dataProvider_testAllJobsDone(self, testdir):
		pAllJobsDone = Proc()
		pAllJobsDone.ppldir = testdir
		yield Jobmgr(pAllJobsDone, RunnerLocal), True
		
		pAllJobsDone1 = Proc()
		pAllJobsDone1.ppldir = testdir
		pAllJobsDone1.cclean = True
		pAllJobsDone1.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pAllJobsDone1._tidyBeforeRun()
		jm1 = Jobmgr(pAllJobsDone1, RunnerLocal)
		yield jm1, False
		
		jm2 = Jobmgr(pAllJobsDone1, RunnerLocal)
		jm2.status[0] = Jobmgr.STATUS_DONE
		jm2.status[1] = Jobmgr.STATUS_DONE
		jm2.status[2] = Jobmgr.STATUS_DONE
		jm2.status[3] = Jobmgr.STATUS_DONEFAILED
		yield jm2, True
		
	def testAllJobsDone(self, jm, ret):
		self.assertEqual(jm.allJobsDone(), ret)
		
	def dataProvider_testCanSubmit(self, testdir):
		pCanSubmit = Proc()
		pCanSubmit.ppldir = testdir
		yield Jobmgr(pCanSubmit, RunnerLocal), True
		
		pCanSubmit1 = Proc()
		pCanSubmit1.ppldir = testdir
		pCanSubmit1.cclean = True
		pCanSubmit1.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pCanSubmit1._tidyBeforeRun()
		jm1 = Jobmgr(pCanSubmit1, RunnerLocal)
		yield jm1, True
		
		jm2 = Jobmgr(pCanSubmit1, RunnerLocal)
		jm2.status[0] = Jobmgr.STATUS_SUBMITTING
		jm2.status[1] = Jobmgr.STATUS_SUBMITTED
		jm2.status[2] = Jobmgr.STATUS_SUBMITFAILED
		jm2.status[3] = Jobmgr.STATUS_SUBMITFAILED
		yield jm2, False
		
	def testCanSubmit(self, jm, ret):
		self.assertEqual(jm.canSubmit(), ret)
		
	def dataProvider_testSubmitPool(self, testdir):
		pSubmitPool = Proc()
		pSubmitPool.ppldir = testdir
		pSubmitPool.cclean = True
		pSubmitPool.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pSubmitPool._tidyBeforeRun()
		jm = Jobmgr(pSubmitPool, RunnerLocal)
		yield jm, [Jobmgr.STATUS_SUBMITTED] * 4
		
		pSubmitPool1 = Proc()
		pSubmitPool1.ppldir = testdir
		pSubmitPool1.cclean = True
		pSubmitPool1.props['ncjobids'] = [0,1,2,3]
		pSubmitPool1.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pSubmitPool1._tidyBeforeRun()
		jm1 = Jobmgr(pSubmitPool1, RunnerLocal)
		helpers.writeFile(pSubmitPool1.jobs[3].script + '.submit', '__notexec__')
		yield jm1, [Jobmgr.STATUS_SUBMITTED] * 3 + [Jobmgr.STATUS_SUBMITFAILED]
	
	# have to use coverage run --concurrency=multiprocessing; coverage report
	def testSubmitPool(self, jm, substatus):
		helpers.log2str()
		sq = JoinableQueue()
		def test(act):
			if act == 'pool':
				jm.submitPool(sq)
			elif act == 'enq':
				for rid in jm.runners.keys():
					sq.put(rid)
				sq.put(None)
			elif act == 'test':
				for k in jm.runners.keys():
					sleep(.6) # stay longer than the waiting period
					self.assertEqual(jm.status[k], substatus[k])
					jm.status[k] = Jobmgr.STATUS_DONE
				
		utils.parallel(test, [('pool', ), ('enq', ), ('test', )], nthread = 3, method = 'process')
	
	def dataProvider_testRunPool(self, testdir):
		pRunPool = Proc()
		pRunPool.ppldir = testdir
		pRunPool.cclean = True
		pRunPool.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pRunPool._tidyBeforeRun()
		jm = Jobmgr(pRunPool, RunnerLocal)
		jm.status[0] = Jobmgr.STATUS_SUBMITTED
		jm.status[1] = Jobmgr.STATUS_SUBMITTED
		jm.status[2] = Jobmgr.STATUS_SUBMITTED
		jm.status[3] = Jobmgr.STATUS_SUBMITTED
		yield jm, [Jobmgr.STATUS_DONE] * 4, [], []
		
		pRunPool1 = Proc()
		pRunPool1.ppldir = testdir
		pRunPool1.cclean = True
		pRunPool1.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pRunPool1._tidyBeforeRun()
		jm1 = Jobmgr(pRunPool1, RunnerLocal)
		jm1.status[0] = Jobmgr.STATUS_SUBMITFAILED
		jm1.status[1] = Jobmgr.STATUS_SUBMITTED
		jm1.status[2] = Jobmgr.STATUS_SUBMITTED
		jm1.status[3] = Jobmgr.STATUS_SUBMITTED
		yield jm1, [Jobmgr.STATUS_DONEFAILED] + [Jobmgr.STATUS_DONE] * 3, [], []
		
		pRunPool2 = Proc()
		pRunPool2.ppldir = testdir
		pRunPool2.cclean = True
		pRunPool2.errhow = 'retry'
		pRunPool2.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pRunPool2._tidyBeforeRun()
		jm2 = Jobmgr(pRunPool2, RunnerLocal)
		jm2.status[0] = Jobmgr.STATUS_SUBMITTED
		jm2.status[1] = Jobmgr.STATUS_SUBMITTED
		jm2.status[2] = Jobmgr.STATUS_SUBMITTED
		jm2.status[3] = Jobmgr.STATUS_SUBMITFAILED
		yield jm2, [Jobmgr.STATUS_DONE] * 3 + [Jobmgr.STATUS_INITIATED], [3], [3]
	
	def testRunPool(self, jm, rstatus, outrq, outsq):
		helpers.log2str()
		rq = JoinableQueue()
		sq = JoinableQueue()
		def test(act):
			if act == 'pool':
				jm.runPool(rq, sq)
			elif act == 'enq':
				for rid in jm.runners.keys():
					rq.put(rid)
				rq.put(None)
			elif act == 'test':
				for k in jm.runners.keys():
					sleep(.6) # stay longer than the waiting period
					self.assertEqual(jm.status[k], rstatus[k])
		utils.parallel(test, [('pool', ), ('enq', ), ('test', )], nthread = 3, method = 'process')
		
		self.assertListEqual(list(_getItemsFromQ(rq)), outrq)
		self.assertListEqual(list(_getItemsFromQ(sq)), outsq)
		
	def dataProvider_testWatchPool(self, testdir):	
		pWatchPool = Proc()
		pWatchPool.ppldir = testdir
		pWatchPool.cclean = True
		pWatchPool.errhow = 'retry'
		pWatchPool.forks  = 5
		pWatchPool.nsub   = 3
		pWatchPool.input  = {'a': [1,2,3,4]}
		with helpers.log2str():
			pWatchPool._tidyBeforeRun()
		jm = Jobmgr(pWatchPool, RunnerLocal)
		jm.status[0] = Jobmgr.STATUS_SUBMITTED
		jm.status[1] = Jobmgr.STATUS_SUBMITTED
		jm.status[2] = Jobmgr.STATUS_SUBMITTED
		jm.status[3] = Jobmgr.STATUS_SUBMITFAILED
		yield jm,
		
	def testWatchPool(self, jm):
		helpers.log2str()
		rq = JoinableQueue()
		sq = JoinableQueue()
		size = len(list(jm.status))
		def test(act):
			if act == 'pool':
				jm.watchPool(rq, sq)
			elif act == 'jobs':
				sleep(.6)
				for i in range(size):
					jm.status[i] = Jobmgr.STATUS_DONE
			elif act == 'test':
				self.assertListEqual(_getItemsFromQ(rq), [])
				self.assertListEqual(_getItemsFromQ(sq), [])
		utils.parallel(test, [('pool', ), ('jobs', ), ('test', )], nthread = 3, method = 'process')	
		self.assertListEqual(_getItemsFromQ(rq), [None] * jm.nprunner)
		self.assertListEqual(_getItemsFromQ(sq), [None] * jm.npsubmit)	
		
	def dataProvider_testProgressBar(self, testdir):
		pProgressbar = Proc()
		pProgressbar.ppldir = testdir
		pProgressbar.cclean = True
		pProgressbar.input  = {'a': [1,2,3,4,5]}
		with helpers.log2str():
			pProgressbar._tidyBeforeRun()
		jm = Jobmgr(pProgressbar, RunnerLocal)
		yield jm, 0, 'INFO', '[1/5] [--------------------------------------------------] Done:   0.0% | Running: 0'
		yield jm, 3, 'INFO', '[4/5] [--------------------------------------------------] Done:   0.0% | Running: 0'
		
		jm1 = Jobmgr(pProgressbar, RunnerLocal)
		jm1.status[0] = Jobmgr.STATUS_SUBMITFAILED
		jm1.status[1] = Jobmgr.STATUS_SUBMITTED
		jm1.status[2] = Jobmgr.STATUS_DONEFAILED
		jm1.status[3] = Jobmgr.STATUS_DONE
		yield jm1, 0, 'SUBMIT', '[1/5] [!!!!!!!!!!>>>>>>>>>>xxxxxxxxxx==========----------] Done:  40.0% | Running: 2'
		
		pProgressbar1 = Proc()
		pProgressbar1.ppldir = testdir
		pProgressbar1.cclean = True
		pProgressbar1.input  = {'a': [1] * 80}
		with helpers.log2str():
			pProgressbar1._tidyBeforeRun()
		jm2 = Jobmgr(pProgressbar1, RunnerLocal)
		yield jm2, 0, 'SUBMIT', '[01/80] [--------------------------------------------------] Done:   0.0% | Running: 0'
		
		jm3 = Jobmgr(pProgressbar1, RunnerLocal)
		jm3.status[0] = Jobmgr.STATUS_DONE
		jm3.status[1] = Jobmgr.STATUS_INITIATED
		jm3.status[2] = Jobmgr.STATUS_DONE
		jm3.status[3] = Jobmgr.STATUS_SUBMITFAILED
		jm3.status[4] = Jobmgr.STATUS_DONE
		jm3.status[5] = Jobmgr.STATUS_SUBMITTED
		jm3.status[6] = Jobmgr.STATUS_DONE
		jm3.status[7] = Jobmgr.STATUS_DONEFAILED
		jm3.status[58] = Jobmgr.STATUS_DONE
		jm3.status[59] = Jobmgr.STATUS_SUBMITFAILED
		jm3.status[60] = Jobmgr.STATUS_DONE
		jm3.status[61] = Jobmgr.STATUS_SUBMITTED
		yield jm3, 0, 'SUBMIT', '[01/80] [-!>x-------------------------!=>------------------] Done:   8.8% | Running: 4'

	def testProgressBar(self, jm, jid, loglevel, bar):
		with helpers.log2str(levels = 'all') as (out, err):
			jm.progressbar(jid, loglevel)
		stderr = err.getvalue()
		self.assertIn(loglevel.upper(), stderr)
		self.assertIn(bar, stderr)
	
	def dataProvider_testRun(self, testdir):
		pRun = Proc()
		pRun.ppldir = testdir
		pRun.cclean = True
		pRun.input  = {'a': [1,2,3,4,5]}
		with helpers.log2str():
			pRun._tidyBeforeRun()
		jm = Jobmgr(pRun, RunnerLocal)
		yield jm,
	
	def testRun(self, jm):
		self.assertIsNone(jm.run())
	
if __name__ == '__main__':
	unittest.main(verbosity=2)