from setuptools import setup, find_packages

# get version
from os import path
verfile = path.join(path.dirname(__file__), 'pyppl', '__init__.py')
with open(verfile) as vf:
	VERSION = vf.readline().split('=')[1].strip()[1:-1]

setup (
	name             = 'PyPPL',
	version          = VERSION,
	description      = "A Python PiPeLine framework",
	url              = "https://github.com/pwwang/PyPPL",
	author           = "pwwang",
	author_email     = "pwwang@pwwang.com",
	license          = "Apache License Version 2.0",
	long_description = "https://github.com/pwwang/PyPPL",
	packages         = find_packages(),
	scripts          = ['bin/pyppl'],
	install_requires = [
		'six', 'filelock', 'futures'
	],
	classifiers      = [
		"Intended Audience :: Developers",
		"Natural Language :: English",
		"Operating System :: MacOS :: MacOS X",
		"Operating System :: POSIX",
		"Operating System :: POSIX :: BSD",
		"Operating System :: POSIX :: Linux",
		"Programming Language :: Python",
		"Programming Language :: Python :: 2",
		"Programming Language :: Python :: 2.7",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.3",
		"Programming Language :: Python :: 3.4",
		"Programming Language :: Python :: 3.5",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
	]
)
