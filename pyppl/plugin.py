"""
Plugin system for PyPPL
@variables:
    PMNAME (str): The name of the plugin manager
    hookimpl (pluggy.HookimplMarker): Used to mark the implementation of hooks
    hookspec (pluggy.HookspecMarker): Used to mark the hooks
"""
# pylint: disable=unused-argument
import sys
import types
import pluggy
from diot import Diot
from .exception import PluginNoSuchPlugin

PMNAME = "pyppl"

# pylint: disable=invalid-name
hookimpl = pluggy.HookimplMarker(PMNAME)
hookspec = pluggy.HookspecMarker(PMNAME)


@hookspec
def setup(config):
    """@API
    PLUGIN API
    Add default configs
    @params:
        config (Config): The default configurations
    """


@hookspec
def proc_init(proc):
    """@API
    PLUGIN API
    Right after a Proc being initialized
    @params:
        proc (Proc): The Proc instance
    """


@hookspec(firstresult=True)
def proc_prerun(proc):
    """@API
    PLUGIN API
    Before a process starts
    If False returned, process will not start
    The value returned by the first plugin will be used, which means
    once a plugin stops process from running, others cannot resume it.
    @params:
        proc (Proc): The Proc instance
    """


@hookspec
def proc_postrun(proc, status):
    """@API
    PLUGIN API
    After a process has done
    @params:
        proc (Proc): The Proc instance
        status (str): succeeded/failed
    """


@hookspec
def pyppl_init(ppl):
    """@API
    PLUGIN API
    Right after a pipeline initiates
    @params:
        ppl (PyPPL): The PyPPL instance
    """


@hookspec(firstresult=True)
def pyppl_prerun(ppl):
    """@API
    PLUGIN API
    Before pipeline starts to run
    If False returned, the pipeline will not run
    The value returned by the first plugin will be used, which means
    once a plugin stops process from running, others cannot resume it.
    @params:
        ppl (PyPPL): The PyPPL instance
    """


@hookspec
def pyppl_postrun(ppl):
    """@API
    PLUGIN API
    After the pipeline is done
    If the pipeline fails, this won't run.
    Use proc_postrun(proc = proc, status = 'failed') instead.
    @params:
        ppl (PyPPL): The PyPPL instance
    """


@hookspec
def job_init(job):
    """@API
    PLUGIN API
    Right after job initiates
    @params:
        job (Job): The Job instance
    """


@hookspec
def job_succeeded(job):
    """@API
    PLUGIN API
    Tell if job is successfully done or not
    One can add not rigorous check. By default, only
    if returncode is 0 checked.
    return False to tell if job is failed otherwise
    use the default status or results from other plugins
    @params:
        job (Job): The Job instance
    """


@hookspec
def job_prebuild(job):
    """@API
    PLUGIN API
    Before a job starts to build
    @params:
        job (Job): The Job instance
    """


@hookspec
def job_build(job, status):
    """@API
    PLUGIN API
    After a job is being built
    @params:
        job (Job): The Job instance
        status (str): The status of the job building
            - True: The job is successfully built
            - False: The job is failed to build
            - cached: The job is cached
    """


@hookspec
def job_submit(job, status):
    """@API
    PLUGIN API
    After a job is being submitted
    @params:
        job (Job): The Job instance
        status (str): The status of the job submission
            - 'succeeded': The job is successfully submitted
            - 'failed': The job is failed to submit
            - 'running': The job is already running
    """


@hookspec
def job_poll(job, status):
    """@API
    PLUGIN API
    Poll the status of a job
    @params:
        job (Job): The Job instance
        status (str): The status of the job
            - 'running': The job is still running
            - 'done': Polling is done, rcfile is generated
    """


@hookspec
def job_kill(job, status):
    """@API
    PLUGIN API
    After a job is being killed
    @params:
        job (Job): The Job instance
        status (str): The status of the job killing
            - 'succeeded': The job is successfully killed
            - 'failed': The job is failed to kill
    """


@hookspec
def job_done(job, status):
    """@API
    PLUGIN API
    After a job is done
    @params:
        job (Job): The Job instance
        status (str): The status of the job
            - succeeded: The job is successfully done
            - failed: The job is failed
            - cached: The job is cached
    """


@hookspec
def logger_init(logger):
    """@API
    PLUGIN API
    Initiate logger, most manipulate levels
    @params:
        logger (Logger): The Logger instance
    """


@hookspec
def cli_addcmd(commands):
    """@API
    PLUGIN API
    Add command and options to CLI
    @params:
        commands (Commands): The Commands instance
    """


@hookspec
def cli_execcmd(command, opts):
    """@API
    PLUGIN API
    Execute the command being added to CLI
    @params:
        command (str): The command
        opts (dict): The options
    """


pluginmgr = pluggy.PluginManager(PMNAME)
pluginmgr.add_hookspecs(sys.modules[__name__])


def _get_plugin(name):
    """
    Try to find the plugin by name with/without prefix.
    If the plugin is not found, try to treat it as a module and import it
    """
    if isinstance(name, str):
        for plugin in pluginmgr.get_plugins():
            plname = pluginmgr.get_name(plugin)
            if plname.isdigit():
                plname = plugin.__class__.__name__
            if plname in ('pyppl-' + name, 'pyppl_' + name,
                          'PyPPL' + name.capitalize()):
                return plugin
        try:
            __import__(name)
        except ImportError as exc:
            raise PluginNoSuchPlugin(name) from exc
    return name


def disable_plugin(plugin):
    """@API
    Try to disable a plugin
    @params:
        plugin (any): A plugin or the name of a plugin
    """
    plugin = _get_plugin(plugin)
    if pluginmgr.is_registered(plugin):
        pluginmgr.unregister(plugin)


def config_plugins(*plugins):
    """@API
    Parse configurations for plugins and enable/disable plugins accordingly.
    @params:
        *plugins ([any]): The plugins
            plugins with 'no:' will be disabled.
    """
    for plugin in plugins:
        if isinstance(plugin, str) and plugin[:3] == 'no:':
            try:
                disable_plugin(_get_plugin(plugin[3:]))
            except PluginNoSuchPlugin:
                pass
        else:
            plugin = _get_plugin(plugin)
            if not pluginmgr.is_registered(plugin):
                if isinstance(plugin, types.ModuleType):
                    pluginmgr.register(plugin)
                else:
                    pluginmgr.register(plugin, name=plugin.__class__.__name__)


class PluginConfig(Diot):
    """@API
    Plugin configuration for Proc/Job"""
    def __init__(self, *args, **kwargs):
        """@API
        Construct for PluginConfig
        @params:
            pconfig (dict): the default plugin configuration
        """
        self.__dict__['_meta'] = Diot(raw={},
                                      converter={},
                                      setcounter={},
                                      updates={})
        super().__init__(*args, **kwargs)
        # reset all counters
        for key in self._meta.setcounter:
            self._meta.setcounter[key] = 0

    def add(self, name, default=None, converter=None, update='update'):
        """@API
        Add a config item
        @params:
            name (str): The name of the config item.
            default (any): The default value
            converter (callable): The converter to convert the value
                whenever the value is set.
            update (str): With setcounter > 1,
                should we update the value or ignore it in .update()?
                - You can set plugin_config_check_update to False with
                    .update to disable this
                - Could be ignore (don't update),
                    replace (replace the whole value, even it is a
                  dictionary) or update
                    (replace the non-dict value and update dictionary values)
        """
        self._meta.converter[name] = converter
        self._meta.updates[name] = update
        # setitem will run the converter
        # if value exists, use it.
        self[name] = self._meta.raw.get(name, default)
        # reset counter
        self._meta.setcounter[name] = 0
        return self

    def update(self, *args, **kwargs):
        """@API
        Update the configuration
        Depends on `update` argument while the configuration is added
        @params:
            pconfig (dict): the configuration to update from
        """
        # if we should check using meta update information or
        # just update directly
        plugin_config_check_update = kwargs.pop("plugin_config_check_update",
                                                True)
        dict_to_update = dict(*args, **kwargs)

        for key, value in dict_to_update.items():

            if plugin_config_check_update and \
             self._meta.updates.get(key, 'update') == 'ignore' and \
             self._meta.setcounter.get(key, 0) > 0:
                continue

            if plugin_config_check_update and \
             self._meta.updates.get(key, 'update') == 'update' and \
             isinstance(value, dict):
                if key in self and isinstance(self[key], dict):
                    self[key].update(value)
                else:
                    self[key] = value
            else:
                self[key] = value

    def __setitem__(self, name, value):
        if name[:6] != '_diot_':
            self._meta.setcounter[name] = \
             self._meta.setcounter.setdefault(name, 0) + 1
            self._meta.raw[name] = value
            if self._meta.converter.get(name):
                value = self._meta.converter[name](value)
        super().__setitem__(name, value)
