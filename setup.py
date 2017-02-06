from setuptools import setup, find_packages
import pyppl

setup (
	name             = 'pyppl',
	version          = pyppl.VERSION,
	description      = "A python lightweight pipeline framework",
	long_description = open('README.md').read(),
	url              = "https://github.com/pwwang/pyppl",
	author           = "pwwang",
	author_email     = "pwwang@pwwang.com",
	license          = "Apache License Version 2.0",
	packages         = find_packages(),
	classifiers      = [
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ]
)