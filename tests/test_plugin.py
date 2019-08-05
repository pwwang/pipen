import sys
import pytest
from pathlib import Path
from pyppl import plugin, PyPPL, Proc, config, __version__

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
pyppl_test      = __import__('pyppl-test')
pyppl_empty     = __import__('pyppl-empty')
pyppl_report    = __import__('pyppl-report')
pyppl_flowchart = __import__('pyppl-flowchart')

def setup_module(module):
	plugin.registerPlugins(['pyppl-test', 'pyppl-empty'], ['pyppl-report', 'pyppl-flowchart'])
	plugin.pluginmgr.hook.setup(config = config)

def teardown_module(module):
	# unregister plugins for further testing
	plugin.pluginmgr.unregister(pyppl_test)
	plugin.pluginmgr.unregister(pyppl_empty)
	plugin.pluginmgr.unregister(pyppl_report)
	plugin.pluginmgr.unregister(pyppl_flowchart)
	config.tplenvs.clear()

def test_register():
	assert plugin.pluginmgr.is_registered(pyppl_test)
	assert plugin.pluginmgr.is_registered(pyppl_report)
	assert plugin.pluginmgr.is_registered(pyppl_flowchart)

def test_prerun(caplog):
	sys.argv = [sys.argv[0]]
	with pytest.raises(plugin.PyPPLFuncWrongPositionError):
		PyPPL().start(Proc(id = 'pPreRun1')).run().preRun()
	assert not any('PYPPL PRERUN' in msg for _,_,msg in caplog.record_tuples)

	PyPPL().start(Proc(id = 'pPreRun2')).preRun().run()
	assert any('PYPPL PRERUN' in msg for _,_,msg in caplog.record_tuples)

def test_postrun(caplog):
	sys.argv = [sys.argv[0]]
	with pytest.raises(plugin.PyPPLFuncWrongPositionError):
		PyPPL().start(Proc(id = 'pPostRun1')).postRun().run()
	assert not any('PYPPL POSTRUN' in msg for _,_,msg in caplog.record_tuples)

	PyPPL().start(Proc(id = 'pPostRun2')).run().postRun()
	assert any('PYPPL POSTRUN' in msg for _,_,msg in caplog.record_tuples)

def test_setgetattr():
	pSetAttr = Proc()
	assert pSetAttr.ptest == 0
	pSetAttr.ptest = 1
	assert pSetAttr.ptest == 100
	assert pSetAttr.pempty == 0
	pSetAttr.pempty = 1
	assert pSetAttr.pempty == 1

def test_prepostrun(caplog):
	p = Proc(id = 'pPrePostRun1')
	p.input = {'a' : ['1']}
	PyPPL().start(p).run()
	expects = [
		'PIPELINE STARTED',
		'pPrePostRun1 STARTED',
		'JOB 0 STARTED',
		'JOB 0 ENDED',
		'pPrePostRun1 ENDED',
		'PIPELINE ENDED'
	]
	for name, level, msg in caplog.record_tuples:
		if expects:
			if expects[0] in msg:
				expects.pop(0)
	assert len(expects) == 0 # messages appear in order

def test_jobfail(caplog):
	p = Proc(id = 'pPluginJobFail')
	p.input = {'a' : ['1']}
	p.script = 'exit 1'
	with pytest.raises(SystemExit):
		PyPPL().start(p).run()
	assert any('Job 0 failed' in msg for _,_,msg in caplog.record_tuples)
