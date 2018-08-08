from collections import OrderedDict

class Box(OrderedDict):
	"""
	Allow dot operation for OrderedDict
	"""

	def __getattr__(self, name):
		if not name.startswith('_OrderedDict') and not name.startswith('__'):
			return self[name]
		return super(Box, self).__getattr__(name)

	def __setattr__(self, name, val):
		if not name.startswith('_OrderedDict') and not name.startswith('__'):
			self[name] = val
		else:
			super(Box, self).__setattr__(name, val)