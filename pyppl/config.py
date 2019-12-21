from multiprocessing import cpu_count
from diot import Diot
from simpleconf import Config
from .plugin import config_plugins, pluginmgr

# priority: lowest -> highest
DEFAULT_CFGFILES = ('~/.PyPPL.toml', './.PyPPL.toml', 'PYPPL.osenv')

# default configurations
DEFAULT_CONFIG = dict(default = dict(
	# plugins
	plugins = ['no:flowchart', 'no:report'],
	# logger options
	logger = dict(
		file       = None,
		theme      = 'greenOnBlack',
		levels     = 'normal',
		leveldiffs = []
	),
	# The cache option, True/False/export
	cache      = True,
	# Whether expand directory to check signature
	dirsig     = True,
	# How to deal with the errors
	# retry, ignore, halt
	# halt to halt the whole pipeline, no submitting new jobs
	# terminate to just terminate the job itself
	errhow     = 'terminate',
	# How many times to retry to jobs once error occurs
	errntry    = 3,
	# The directory to export the output files
	forks      = 1,
	# Default shell/language
	lang       = 'bash',
	# number of threads used to build jobs and to check job cache status
	nthread    = min(int(cpu_count() / 2), 16),
	# Where cache file and workdir located
	ppldir     = './workdir',
	# Select the runner
	runner     = 'local',
	# The tag of the job
	tag        = 'notag',
	# The template engine (name)
	template   = 'liquid',
	# The template environment
	envs       = Diot(),
	# configs for plugins
	plugin_config = {},
))

config = Config()
def load_config(default_config, *config_files):
	config.clear()
	config._load(default_config, *config_files)
	config._use()

load_config(DEFAULT_CONFIG, *DEFAULT_CFGFILES)
config_plugins(*config.plugins)
pluginmgr.hook.setup(config = config)