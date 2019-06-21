# module: pyppl
The main module of PyPPL  
!!! example "class: `Path`"
PurePath subclass that can make system calls.  
  
    Path represents a filesystem path but unlike PurePath, also offers  
    methods to do system calls on path objects. Depending on your system,  
    instantiating a Path will return either a PosixPath or a WindowsPath  
    object. You can also instantiate a PosixPath or WindowsPath directly,  
    but cannot instantiate a WindowsPath on a POSIX system or vice versa.  
  
	!!! tip "staticmethod: `__enter__ (self)`"
  
	!!! tip "staticmethod: `__exit__ (self, t, v, tb)`"
  
	!!! tip "staticmethod: `__new__ (cls, *args, **kwargs)`"
  
	!!! tip "staticmethod: `absolute (self)`"
Return an absolute version of this path.  This function works  
        even if the path doesn't point to anything.  
  
        No normalization is done, i.e. all '.' and '..' will be kept along.  
        Use resolve() to get the canonical path to a file.  
  
	!!! tip "staticmethod: `chmod (self, mode)`"
  
        Change the permissions of the path, like os.chmod().  
  
	!!! abstract "method: `cwd (cls)`"
Return a new path pointing to the current working directory  
        (as returned by os.getcwd()).  
  
	!!! tip "staticmethod: `exists (self)`"
  
        Whether this path exists.  
  
	!!! tip "staticmethod: `expanduser (self)`"
 Return a new path with expanded ~ and ~user constructs  
        (as returned by os.path.expanduser)  
  
	!!! tip "staticmethod: `group (self)`"
  
        Return the group name of the file gid.  
  
	!!! abstract "method: `home (cls)`"
Return a new path pointing to the user's home directory (as  
        returned by os.path.expanduser('~')).  
  
	!!! tip "staticmethod: `is_block_device (self)`"
  
        Whether this path is a block device.  
  
	!!! tip "staticmethod: `is_char_device (self)`"
  
        Whether this path is a character device.  
  
	!!! tip "staticmethod: `is_dir (self)`"
  
        Whether this path is a directory.  
  
	!!! tip "staticmethod: `is_fifo (self)`"
  
        Whether this path is a FIFO.  
  
	!!! tip "staticmethod: `is_file (self)`"
  
        Whether this path is a regular file (also True for symlinks pointing  
        to regular files).  
  
	!!! tip "staticmethod: `is_mount (self)`"
  
        Check if this path is a POSIX mount point  
  
	!!! tip "staticmethod: `is_socket (self)`"
  
        Whether this path is a socket.  
  
	!!! tip "staticmethod: `is_symlink (self)`"
  
        Whether this path is a symbolic link.  
  
	!!! tip "staticmethod: `iterdir (self)`"
Iterate over the files in this directory.  Does not yield any  
        result for the special paths '.' and '..'.  
  
	!!! tip "staticmethod: `lchmod (self, mode)`"
  
        Like chmod(), except if the path points to a symlink, the symlink's  
        permissions are changed, rather than its target's.  
  
	!!! tip "staticmethod: `lstat (self)`"
  
        Like stat(), except if the path points to a symlink, the symlink's  
        status information is returned, rather than its target's.  
  
	!!! tip "staticmethod: `mkdir (self, mode, parents, exist_ok)`"
  
        Create a new directory at this given path.  
  
	!!! tip "staticmethod: `open (self, mode, buffering, encoding, errors, newline)`"
  
        Open the file pointed by this path and return a file object, as  
        the built-in open() function does.  
  
	!!! tip "staticmethod: `owner (self)`"
  
        Return the login name of the file owner.  
  
	!!! tip "staticmethod: `read_bytes (self)`"
  
        Open the file in bytes mode, read it, and close the file.  
  
	!!! tip "staticmethod: `read_text (self, encoding, errors)`"
  
        Open the file in text mode, read it, and close the file.  
  
	!!! tip "staticmethod: `rename (self, target)`"
  
        Rename this path to the given path.  
  
	!!! tip "staticmethod: `replace (self, target)`"
  
        Rename this path to the given path, clobbering the existing  
        destination if it exists.  
  
	!!! tip "staticmethod: `resolve (self, strict)`"
  
        Make the path absolute, resolving all symlinks on the way and also  
        normalizing it (for example turning slashes into backslashes under  
        Windows).  
  
	!!! tip "staticmethod: `rglob (self, pattern)`"
Recursively yield all existing files (of any kind, including  
        directories) matching the given pattern, anywhere in this subtree.  
  
	!!! tip "staticmethod: `rmdir (self)`"
  
        Remove this directory.  The directory must be empty.  
  
	!!! tip "staticmethod: `samefile (self, other_path)`"
Return whether other_path is the same or not as this file  
        (as returned by os.path.samefile()).  
  
	!!! tip "staticmethod: `stat (self)`"
  
        Return the result of the stat() system call on this path, like  
        os.stat() does.  
  
	!!! tip "staticmethod: `symlink_to (self, target, target_is_directory)`"
  
        Make this path a symlink pointing to the given path.  
        Note the order of arguments (self, target) is the reverse of os.symlink's.  
  
	!!! tip "staticmethod: `touch (self, mode, exist_ok)`"
  
        Create this file with the given access mode, if it doesn't exist.  
  
	!!! tip "staticmethod: `unlink (self)`"
  
        Remove this file or link.  
        If the path is a directory, use rmdir() instead.  
  
	!!! tip "staticmethod: `write_bytes (self, data)`"
  
        Open the file in bytes mode, write to it, and close the file.  
  
	!!! tip "staticmethod: `write_text (self, data, encoding, errors)`"
  
        Open the file in text mode, write to it, and close the file.  
  
!!! example "class: `Proxy`"
  
	A proxy class extended from list to enable dot access  
	to all members and set attributes for all members.  
  
	!!! tip "staticmethod: `__getattr__ (self, item)`"
  
	!!! tip "staticmethod: `__getitem__ (self, item)`"
  
	!!! tip "staticmethod: `__setattr__ (self, name, value)`"
  
	!!! tip "staticmethod: `__setitem__ (self, item, value)`"
  
	!!! tip "staticmethod: `add (self, anything)`"
  
		Add elements to the list.  

		- **params:**  
			`anything`: anything that is to be added.  
				If it is a Proxy, element will be added individually  
				Otherwise the whole `anything` will be added as one element.  
  
!!! example "class: `PyPPL`"
  
	The PyPPL class  
  

	- **static variables:**  
		`TIPS`: The tips for users  
		`RUNNERS`: Registered runners  
		`DEFAULT_CFGFILES`: Default configuration file  
		`COUNTER`: The counter for `PyPPL` instance  
  
	!!! tip "staticmethod: `__init__ (self, conf, cfgfile)`"
  
		Constructor  

		- **params:**  
			`conf`: the configurations for the pipeline, default: {}  
			`cfgfile`: the configuration file for the pipeline, default: None  
  
	!!! tip "staticmethod: `flowchart (self, fcfile, dotfile)`"
  
		Generate graph in dot language and visualize it.  

		- **params:**  
			`dotfile`: Where to same the dot graph.  
				- Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.dot"`)  
			`fcfile`:  The flowchart file.  
				- Default: `None` (`path.splitext(sys.argv[0])[0] + ".pyppl.svg"`)  
				- For example: run `python pipeline.py` will save it to `pipeline.pyppl.svg`  

		- **returns:**  
			The pipeline object itself.  
  
	!!! tip "staticmethod: `registerRunner (runner_to_reg)`"
  
		Register a runner  

		- **params:**  
			`runner`: The runner to be registered.  
  
	!!! tip "staticmethod: `resume (self, *args)`"
  
		Mark processes as to be resumed  

		- **params:**  
			`args`: the processes to be marked  

		- **returns:**  
			The pipeline object itself.  
  
	!!! tip "staticmethod: `resume2 (self, *args)`"
  
		Mark processes as to be resumed  

		- **params:**  
			`args`: the processes to be marked  

		- **returns:**  
			The pipeline object itself.  
  
	!!! tip "staticmethod: `run (self, profile)`"
  
		Run the pipeline  

		- **params:**  
			`profile`: the profile used to run, if not found, it'll be used as runner name.  
				- default: 'default'  

		- **returns:**  
			The pipeline object itself.  
  
	!!! tip "staticmethod: `showAllRoutes (self)`"
  
		Show all the routes in the log.  
  
	!!! tip "staticmethod: `start (self, *args)`"
  
		Set the starting processes of the pipeline  

		- **params:**  
			`args`: the starting processes  

		- **returns:**  
			The pipeline object itself.  
  
# module: pyppl.proc
  
proc module for PyPPL  
  
!!! example "class: `ProcSet`"
  
	The ProcSet for a set of processes  
  
	!!! tip "staticmethod: `__getattr__ (self, item)`"
  
	!!! tip "staticmethod: `__getitem__ (self, item, _ignore_default)`"
Process selector, always return Proxy object  
	!!! tip "staticmethod: `__init__ (self, *procs, **kwargs)`"
  
		Constructor  

		- **params:**  
			`*procs` : the set of processes  
			`depends`: Whether auto deduce depends. Default: True  
			`id`     : The id of the procset. Default: None (the variable name)  
			`tag`    : The tag of the processes. Default: None (a unique 4-char str according to the id)  
			`copy`   : Whether copy the processes or just use them. Default: `True`  
  
	!!! tip "staticmethod: `__setattr__ (self, item, value)`"
  
	!!! tip "staticmethod: `copy (self, id, tag, depends)`"
  
		Like `proc`'s `copy` function, copy a procset. Each processes will be copied.  

		- **params:**  
			`id`     : Use a different id if you don't want to use the variant name  
			`tag`    : The new tag of all copied processes  
			`depends`: Whether to copy the dependencies or not. Default: True  
				- dependences for processes in starts will not be copied  

		- **returns:**  
			The new procset  
  
	!!! tip "staticmethod: `delegate (self, *procs)`"
  
	!!! tip "staticmethod: `delegated (self, name)`"
  
	!!! tip "staticmethod: `module (self, name)`"
  
	!!! tip "staticmethod: `restoreStates (self)`"
  
!!! example "class: `Path`"
PurePath subclass that can make system calls.  
  
    Path represents a filesystem path but unlike PurePath, also offers  
    methods to do system calls on path objects. Depending on your system,  
    instantiating a Path will return either a PosixPath or a WindowsPath  
    object. You can also instantiate a PosixPath or WindowsPath directly,  
    but cannot instantiate a WindowsPath on a POSIX system or vice versa.  
  
	!!! tip "staticmethod: `__enter__ (self)`"
  
	!!! tip "staticmethod: `__exit__ (self, t, v, tb)`"
  
	!!! tip "staticmethod: `__new__ (cls, *args, **kwargs)`"
  
	!!! tip "staticmethod: `absolute (self)`"
Return an absolute version of this path.  This function works  
        even if the path doesn't point to anything.  
  
        No normalization is done, i.e. all '.' and '..' will be kept along.  
        Use resolve() to get the canonical path to a file.  
  
	!!! tip "staticmethod: `chmod (self, mode)`"
  
        Change the permissions of the path, like os.chmod().  
  
	!!! abstract "method: `cwd (cls)`"
Return a new path pointing to the current working directory  
        (as returned by os.getcwd()).  
  
	!!! tip "staticmethod: `exists (self)`"
  
        Whether this path exists.  
  
	!!! tip "staticmethod: `expanduser (self)`"
 Return a new path with expanded ~ and ~user constructs  
        (as returned by os.path.expanduser)  
  
	!!! tip "staticmethod: `group (self)`"
  
        Return the group name of the file gid.  
  
	!!! abstract "method: `home (cls)`"
Return a new path pointing to the user's home directory (as  
        returned by os.path.expanduser('~')).  
  
	!!! tip "staticmethod: `is_block_device (self)`"
  
        Whether this path is a block device.  
  
	!!! tip "staticmethod: `is_char_device (self)`"
  
        Whether this path is a character device.  
  
	!!! tip "staticmethod: `is_dir (self)`"
  
        Whether this path is a directory.  
  
	!!! tip "staticmethod: `is_fifo (self)`"
  
        Whether this path is a FIFO.  
  
	!!! tip "staticmethod: `is_file (self)`"
  
        Whether this path is a regular file (also True for symlinks pointing  
        to regular files).  
  
	!!! tip "staticmethod: `is_mount (self)`"
  
        Check if this path is a POSIX mount point  
  
	!!! tip "staticmethod: `is_socket (self)`"
  
        Whether this path is a socket.  
  
	!!! tip "staticmethod: `is_symlink (self)`"
  
        Whether this path is a symbolic link.  
  
	!!! tip "staticmethod: `iterdir (self)`"
Iterate over the files in this directory.  Does not yield any  
        result for the special paths '.' and '..'.  
  
	!!! tip "staticmethod: `lchmod (self, mode)`"
  
        Like chmod(), except if the path points to a symlink, the symlink's  
        permissions are changed, rather than its target's.  
  
	!!! tip "staticmethod: `lstat (self)`"
  
        Like stat(), except if the path points to a symlink, the symlink's  
        status information is returned, rather than its target's.  
  
	!!! tip "staticmethod: `mkdir (self, mode, parents, exist_ok)`"
  
        Create a new directory at this given path.  
  
	!!! tip "staticmethod: `open (self, mode, buffering, encoding, errors, newline)`"
  
        Open the file pointed by this path and return a file object, as  
        the built-in open() function does.  
  
	!!! tip "staticmethod: `owner (self)`"
  
        Return the login name of the file owner.  
  
	!!! tip "staticmethod: `read_bytes (self)`"
  
        Open the file in bytes mode, read it, and close the file.  
  
	!!! tip "staticmethod: `read_text (self, encoding, errors)`"
  
        Open the file in text mode, read it, and close the file.  
  
	!!! tip "staticmethod: `rename (self, target)`"
  
        Rename this path to the given path.  
  
	!!! tip "staticmethod: `replace (self, target)`"
  
        Rename this path to the given path, clobbering the existing  
        destination if it exists.  
  
	!!! tip "staticmethod: `resolve (self, strict)`"
  
        Make the path absolute, resolving all symlinks on the way and also  
        normalizing it (for example turning slashes into backslashes under  
        Windows).  
  
	!!! tip "staticmethod: `rglob (self, pattern)`"
Recursively yield all existing files (of any kind, including  
        directories) matching the given pattern, anywhere in this subtree.  
  
	!!! tip "staticmethod: `rmdir (self)`"
  
        Remove this directory.  The directory must be empty.  
  
	!!! tip "staticmethod: `samefile (self, other_path)`"
Return whether other_path is the same or not as this file  
        (as returned by os.path.samefile()).  
  
	!!! tip "staticmethod: `stat (self)`"
  
        Return the result of the stat() system call on this path, like  
        os.stat() does.  
  
	!!! tip "staticmethod: `symlink_to (self, target, target_is_directory)`"
  
        Make this path a symlink pointing to the given path.  
        Note the order of arguments (self, target) is the reverse of os.symlink's.  
  
	!!! tip "staticmethod: `touch (self, mode, exist_ok)`"
  
        Create this file with the given access mode, if it doesn't exist.  
  
	!!! tip "staticmethod: `unlink (self)`"
  
        Remove this file or link.  
        If the path is a directory, use rmdir() instead.  
  
	!!! tip "staticmethod: `write_bytes (self, data)`"
  
        Open the file in bytes mode, write to it, and close the file.  
  
	!!! tip "staticmethod: `write_text (self, data, encoding, errors)`"
  
        Open the file in text mode, write to it, and close the file.  
  
!!! example "class: `NoSuchProfile`"
Raises when configuration profile does not exist  
!!! example "class: `Proc`"
  
	The Proc class defining a process  
  

	- **static variables:**  
		`ALIAS`:         The alias for the properties  
		`DEPRECATED`:    Deprecated property names  
  
		`OUT_VARTYPE`:    Variable types for output  
		`OUT_FILETYPE`:   File types for output  
		`OUT_DIRTYPE`:    Directory types for output  
		`OUT_STDOUTTYPE`: Stdout types for output  
		`OUT_STDERRTYPE`: Stderr types for output  
  
		`IN_VARTYPE`:   Variable types for input  
		`IN_FILETYPE`:  File types for input  
		`IN_FILESTYPE`: Files types for input  
  
		`EX_GZIP`: `exhow` value to gzip output files while exporting them  
		`EX_COPY`: `exhow` value to copy output files while exporting them  
		`EX_MOVE`: `exhow` value to move output files while exporting them  
		`EX_LINK`: `exhow` value to link output files while exporting them  
  
	!!! tip "staticmethod: `__getattr__ (self, name)`"
  
		Get the value of a property in `self.props`  
		It recognizes alias as well.  

		- **params:**  
			`name`: The name of the property  

		- **returns:**  
			The value of the property  
  
	!!! tip "staticmethod: `__init__ (self, id, tag, desc, **kwargs)`"
  
		Constructor  

		- **params:**  
			`tag`     : The tag of the process  
			`desc`    : The description of the process  
			`id`      : The identify of the process  
			`**kwargs`: Other properties of the process, which can be set by `proc.xxx` later.  

		- **config:**  
			id, input, output, ppldir, forks, cache, acache, rc, echo, runner, script, depends,  
			tag, desc, dirsig, exdir, exhow, exow, errhow, errntry, lang, beforeCmd, afterCmd,  
			workdir, args, callfront, callback, expect, expart, template, tplenvs,  
			resume, nthread  

		- **props**  
			input, output, rc, echo, script, depends, beforeCmd, afterCmd, workdir, expect  
			expart, template, channel, jobs, ncjobids, size, sets, procvars, suffix  
  
	!!! tip "staticmethod: `__setattr__ (self, name, value)`"
  
		Set the value of a property in `self.config`  

		- **params:**  
			`name` : The name of the property.  
			`value`: The new value of the property.  
  
	!!! tip "staticmethod: `copy (self, id, tag, desc)`"
  
		Copy a process  

		- **params:**  
			`id`: The new id of the process, default: `None` (use the varname)  
			`tag`:   The tag of the new process, default: `None` (used the old one)  
			`desc`:  The desc of the new process, default: `None` (used the old one)  

		- **returns:**  
			The new process  
  
	!!! tip "staticmethod: `name (self, procset)`"
  
		Get my name include `procset`, `id`, `tag`  

		- **returns:**  
			the name  
  
	!!! tip "staticmethod: `run (self, profile, config)`"

- **api**  
		Run the process with a profile and/or a configuration  

		- **params:**  
			profile (str): The profile from a configuration file.  
			config (dict): A configuration passed to PyPPL construct.  
  
!!! example "class: `OBox`"
Ordered Box  
	!!! tip "staticmethod: `__init__ (self, *args, **kwargs)`"
  
	!!! abstract "method: `from_json (cls, json_string, filename, encoding, errors, **kwargs)`"
  
        Transform a json object string into a Box object. If the incoming  
        json is a list, you must use BoxList.from_json.  
  
        :param json_string: string to pass to `json.loads`  
        :param filename: filename to open and pass to `json.load`  
        :param encoding: File encoding  
        :param errors: How to handle encoding errors  
        :param kwargs: parameters to pass to `Box()` or `json.loads`  
        :return: Box object from json data  
  
	!!! abstract "method: `from_yaml (cls, yaml_string, filename, encoding, errors, loader, **kwargs)`"
  
            Transform a yaml object string into a Box object.  
  
            :param yaml_string: string to pass to `yaml.load`  
            :param filename: filename to open and pass to `yaml.load`  
            :param encoding: File encoding  
            :param errors: How to handle encoding errors  
            :param loader: YAML Loader, defaults to SafeLoader  
            :param kwargs: parameters to pass to `Box()` or `yaml.load`  
            :return: Box object from yaml data  
  
	!!! abstract "method: `fromkeys (type, iterable, value)`"
Create a new dictionary with keys from iterable and values set to value.  
!!! example "class: `Hashable`"
  
	A class for object that can be hashable  
  
!!! example "class: `Box`"
  
	Subclass of box.Box to fix box_intact_types to [list] and  
	rewrite __repr__ to make the string results back to object  
	Requires python-box ^3.4.1  
  
	!!! tip "staticmethod: `__init__ (self, *args, **kwargs)`"
  
	!!! abstract "method: `from_json (cls, json_string, filename, encoding, errors, **kwargs)`"
  
        Transform a json object string into a Box object. If the incoming  
        json is a list, you must use BoxList.from_json.  
  
        :param json_string: string to pass to `json.loads`  
        :param filename: filename to open and pass to `json.load`  
        :param encoding: File encoding  
        :param errors: How to handle encoding errors  
        :param kwargs: parameters to pass to `Box()` or `json.loads`  
        :return: Box object from json data  
  
	!!! abstract "method: `from_yaml (cls, yaml_string, filename, encoding, errors, loader, **kwargs)`"
  
            Transform a yaml object string into a Box object.  
  
            :param yaml_string: string to pass to `yaml.load`  
            :param filename: filename to open and pass to `yaml.load`  
            :param encoding: File encoding  
            :param errors: How to handle encoding errors  
            :param loader: YAML Loader, defaults to SafeLoader  
            :param kwargs: parameters to pass to `Box()` or `yaml.load`  
            :return: Box object from yaml data  
  
	!!! abstract "method: `fromkeys (type, iterable, value)`"
Create a new dictionary with keys from iterable and values set to value.  
