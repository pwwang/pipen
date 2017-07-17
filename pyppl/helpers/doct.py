

class doct(dict):
	"""
	Extend dict so you can use dot (".") to access keys.
	Refer to 
	Examples:
	```python
	m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
	# Add new key
	m.new_key = 'Hello world!'
	# Or
	m['new_key'] = 'Hello world!'
	print m.new_key
	print m['new_key']
	# Update values
	m.new_key = 'Yay!'
	# Or
	m['new_key'] = 'Yay!'
	# Delete key
	del m.new_key
	# Or
	del m['new_key']
	```
	"""

	def __init__(self, *args, **kwargs):
		super(doct, self).__init__(*args, **kwargs)
		for arg in args:
			if isinstance(arg, dict):
				for k, v in arg.items():
					self[k] = doct(v) if isinstance(v, dict) else v
			elif isinstance(arg, doct):
				self = doct

		if kwargs:
			for k, v in kwargs.items():
				self[k] = doct(v) if isinstance(v, dict) else v

	def __getattr__(self, attr):
		return self.get(attr)

	def __setattr__(self, key, value):
		self.__setitem__(key, doct(value) if isinstance(value, dict) else value)

	def __setitem__(self, key, value):
		doct(value) if isinstance(value, dict) else value
		super(doct, self).__setitem__(key, value)
		self.__dict__.update({key: value})

	def __delattr__(self, item):
		self.__delitem__(item)

	def __delitem__(self, key):
		super(doct, self).__delitem__(key)
		del self.__dict__[key]