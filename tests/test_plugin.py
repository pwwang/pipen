import pytest
import types
from diot import Diot
from pyppl import PyPPL
from pyppl.plugin import PluginConfig, _get_plugin, pluginmgr, disable_plugin, config_plugins, hookimpl
from pyppl.exception import PluginNoSuchPlugin
from pyppl.logger import Logger

class PyPPLPlugin:
    pass


class PyPPLMPlugin(types.ModuleType):
    pass


def test_get_plugin():
    plugin = PyPPLPlugin()
    pluginmgr.register(plugin)
    assert isinstance(_get_plugin('plugin'), PyPPLPlugin)

    pluginmgr.unregister(plugin)
    pluginmgr.register(PyPPLPlugin)
    assert _get_plugin('plugin') is PyPPLPlugin
    assert _get_plugin(PyPPLPlugin) is PyPPLPlugin
    pluginmgr.unregister(PyPPLPlugin)


def test_disable_plugin():
    plugin = PyPPLPlugin()
    pluginmgr.register(plugin)
    assert pluginmgr.is_registered(plugin)
    disable_plugin(plugin)
    assert not pluginmgr.is_registered(plugin)


def test_config_plugins():
    plugin = PyPPLPlugin()
    pluginmgr.register(plugin)
    config_plugins('no:plugin', 'no:x')
    assert not pluginmgr.is_registered(plugin)
    with pytest.raises(PluginNoSuchPlugin):
        config_plugins('plugin')

    config_plugins(1)
    config_plugins(PyPPLMPlugin(name='pyppl_mplugin'))


def test_plugin_config():

    pconfig = PluginConfig({'a': 1})
    assert pconfig == {'a': 1}
    assert list(pconfig.items()) == [('a', 1)]
    assert pconfig.a == 1
    assert pconfig._meta.setcounter.get('a', 0) == 0

    pconfig = PluginConfig()
    assert pconfig._meta.raw == {}
    assert pconfig == {}
    assert pconfig._meta.converter == {}

    pconfig.add('a')
    assert pconfig.a is None
    assert pconfig._meta.setcounter.get('a', 0) == 0

    pconfig.add('b', default=1, converter=lambda v: v + 1)
    assert pconfig.b == 2
    assert pconfig._meta.setcounter.get('b', 0) == 0
    pconfig.b = 2
    assert pconfig._meta.setcounter.get('b', 0) == 1
    assert pconfig.b == 3

    pconfig['r.a'] = 4
    assert pconfig._meta.setcounter.get('r.a', 0) == 1
    assert pconfig['r.a'] == 4

    pconfig.add('x', update='ignore')
    pconfig.update({'x': 1})
    assert pconfig.x == 1
    pconfig.x = 10
    pconfig.update({'x': 1})
    assert pconfig.x == 10

    pconfig.add('z', default=0, update='update', converter=lambda x: x * 2)
    pconfig.z = 10
    assert pconfig.z == 20
    pconfig.update({'z': 1})
    assert pconfig.z == 2
    assert pconfig.z == 2  # use cache

    pconfig.add('c', update='update', converter=lambda x: x or {})
    assert pconfig.c == {}
    pconfig.update({'c': {'x': 1, 'm': 0}})
    assert pconfig.c['x'] == 1
    pconfig.update({'c': {'x': 2}})
    assert pconfig.c['x'] == 2
    assert pconfig.c['m'] == 0

    pconfig.add('d', update='replace')
    pconfig.d = {'a': 1, 'b': 2}
    assert pconfig.d == {'a': 1, 'b': 2}
    pconfig.d = {'a': 3}
    assert pconfig.d == {'a': 3}

    pconfig.add('e')
    pconfig.update(e={})
    assert pconfig.e == {}

    pconfig.update({'y': 2})


# test hooks
def test_job_is_succeeded(tmp_path):
    class PyPPLJobIsSucceeded:
        @hookimpl
        def job_succeeded(self, job):
            return False

    pluginmgr.register(PyPPLJobIsSucceeded())
    from pyppl.job import Job
    workdir = tmp_path.joinpath('pJobIsSucceeded')
    workdir.mkdir()
    job = Job(0, Diot(workdir=workdir))
    job.dir.mkdir(parents=True, exist_ok=True)
    assert not job.is_succeeded()


def test_job_done(tmp_path, capsys):
    class PyPPLJobDone:
        @hookimpl
        def job_done(self, job, status):
            print(status)

    pluginmgr.register(PyPPLJobDone())
    from pyppl.job import Job
    workdir = tmp_path.joinpath('pJobDone')
    workdir.mkdir()
    job = Job(
        0,
        Diot(workdir=workdir,
             id='pJobDone',
             shortname='pJobDone',
             size=0,
             cache=True,
             input={},
             output={}))
    job.dir.mkdir(parents=True, exist_ok=True)
    job.done(cached=True)
    assert 'cached' in capsys.readouterr().out


def test_job_submit(tmp_path, capsys, caplog):
    class PyPPLJobSubmit:
        @hookimpl
        def job_submit(self, job, status):
            print(status)

    from pyppl.runner import hookimpl as runner_hookimpl, register_runner, use_runner

    class PyPPLRunnerIsRunning:
        @runner_hookimpl
        def isrunning(self, job):
            return True

    class PyPPLRunnerSubmitFail:
        @runner_hookimpl
        def submit(self, job):
            return Diot(rc=1, cmd='helloworld', stderr='stderr')

    register_runner(PyPPLRunnerIsRunning(), 'isrunning')
    register_runner(PyPPLRunnerSubmitFail(), 'submitfail')
    use_runner('isrunning')

    pluginmgr.register(PyPPLJobSubmit())
    from pyppl.job import Job
    from pyppl.template import TemplateLiquid
    workdir = tmp_path.joinpath('pJobSubmit')
    workdir.mkdir()
    job = Job(
        0,
        Diot(workdir=workdir,
             id='pJobSubmit',
             shortname='pJobSubmit',
             size=0,
             cache=True,
             input={},
             output={},
             script=TemplateLiquid(''),
             runner='isrunning'))
    job.dir.mkdir(parents=True, exist_ok=True)
    job.submit()
    assert 'running' in capsys.readouterr().out

    use_runner('submitfail')
    job.submit()
    assert 'Submission failed (rc = 1, cmd = helloworld)' in caplog.text


def test_job_kill(tmp_path, capsys, caplog):
    class PyPPLJobKill:
        @hookimpl
        def job_kill(self, job, status):
            print(status)

    from pyppl.runner import hookimpl as runner_hookimpl, register_runner, use_runner

    class PyPPLRunnerKill:
        @runner_hookimpl
        def kill(self, job):
            return True

    register_runner(PyPPLRunnerKill(), 'kill')
    use_runner('kill')

    pluginmgr.register(PyPPLJobKill())
    from pyppl.job import Job
    from pyppl.template import TemplateLiquid
    workdir = tmp_path.joinpath('pJobKill')
    workdir.mkdir()
    job = Job(
        0,
        Diot(workdir=workdir,
             id='pJobKill',
             shortname='pJobKill',
             size=0,
             cache=True,
             input={},
             output={},
             script=TemplateLiquid(''),
             runner='isrunning'))
    job.dir.mkdir(parents=True, exist_ok=True)
    assert job.kill()
    assert 'succeeded' in capsys.readouterr().out


def test_pyppl_prerun_stop_run(tmp_path, caplog):
    logger = Logger(plugin="stoprun")
    class PyPPLStopRun:
        @hookimpl
        def pyppl_prerun(self, ppl):
            logger.info("Stopped.")
            return False

        @hookimpl
        def pyppl_postrun(self, ppl):
            ppl.props.x = 1
    pluginmgr.register(PyPPLStopRun())
    ppl = PyPPL().run()
    assert ppl.props.x == 1

    assert "STOPRUN.   INFO] Stopped." in caplog.text
