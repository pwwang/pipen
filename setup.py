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
	packages         = find_packages(),
	scripts          = ['bin/pyppl'],
	install_requires=[
		'python-box', 'six', 'filelock'
    ],
)
