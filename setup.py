from setuptools import setup, find_packages

setup (
	name = 'pyppl',
	version = '0.1.0',
	description = 'A python lightweight pipeline framework',
	url = 'https://github.com/pwwang/pyppl',
	author='pwwang',
	author_email='pwwang@pwwang.com',
	license='MIT',
	packages=find_packages(exclude=['test'])
)